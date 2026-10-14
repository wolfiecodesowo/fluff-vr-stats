package com.wolfiecodesowo.fluffvr

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.pose.PoseDetection
import com.google.mlkit.vision.pose.PoseLandmark
import com.google.mlkit.vision.pose.defaults.PoseDetectorOptions
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/**
 * Phone camera body tracker (v0.10). Put ur phone on the floor / a shelf facing u (whole body in view), pair it
 * with ur Quest in the Remote tab, tap start: it finds ur hips, knees, feet + elbows on the phone (ML Kit, all
 * on-device, no account) and sends VRChat trackers through the Quest app. Calibrate FBT in VRChat like normal.
 */
class TrackerService : Service() {
    private lateinit var thread: HandlerThread
    private lateinit var handler: Handler
    private var camera: CameraDevice? = null
    private var session: CameraCaptureSession? = null
    private var reader: ImageReader? = null
    private val detector by lazy {
        PoseDetection.getClient(PoseDetectorOptions.Builder().setDetectorMode(PoseDetectorOptions.STREAM_MODE).build())
    }
    @Volatile private var busy = false
    private var sock: DatagramSocket? = null
    private var math: PoseMath? = null
    private var frames = 0
    private var rateT = System.currentTimeMillis()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        running = true
        status = "starting the camera…"
        startForeground(3, notification())
        thread = HandlerThread("fluff-tracker").also { it.start() }
        handler = Handler(thread.looper)
        handler.post { openCamera() }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "calibrate") recalibrate = true
        return START_NOT_STICKY
    }

    @SuppressLint("MissingPermission")
    private fun openCamera() {
        val s = Settings(this)
        val cm = getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val want = if (s.trackFront) CameraCharacteristics.LENS_FACING_FRONT else CameraCharacteristics.LENS_FACING_BACK
        val id = cm.cameraIdList.firstOrNull { cm.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) == want }
            ?: cm.cameraIdList.firstOrNull()
        if (id == null) { status = "no camera found"; return }
        rotation = cm.getCameraCharacteristics(id).get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 90
        val r = ImageReader.newInstance(640, 480, ImageFormat.YUV_420_888, 3)
        reader = r
        r.setOnImageAvailableListener({ rd ->
            val img = rd.acquireLatestImage() ?: return@setOnImageAvailableListener
            if (busy) { img.close(); return@setOnImageAvailableListener }
            busy = true
            val input = InputImage.fromMediaImage(img, rotation)
            detector.process(input)
                .addOnSuccessListener { pose -> onPose(pose, input.width, input.height) }
                .addOnFailureListener { status = "pose error: ${it.message}" }
                .addOnCompleteListener { img.close(); busy = false }
        }, handler)
        try {
            cm.openCamera(id, object : CameraDevice.StateCallback() {
                override fun onOpened(cd: CameraDevice) {
                    camera = cd
                    @Suppress("DEPRECATION")
                    cd.createCaptureSession(listOf(r.surface), object : CameraCaptureSession.StateCallback() {
                        override fun onConfigured(cs: CameraCaptureSession) {
                            session = cs
                            val req = cd.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW).apply { addTarget(r.surface) }
                            cs.setRepeatingRequest(req.build(), null, handler)
                            status = "looking for u ~ stand back so ur whole body fits"
                        }
                        override fun onConfigureFailed(cs: CameraCaptureSession) { status = "camera setup failed" }
                    }, handler)
                }
                override fun onDisconnected(cd: CameraDevice) { cd.close(); status = "camera disconnected" }
                override fun onError(cd: CameraDevice, e: Int) { cd.close(); status = "camera error $e" }
            }, handler)
        } catch (e: SecurityException) { status = "allow the camera for Fluff VR Stats first" }
    }

    private fun onPose(pose: com.google.mlkit.vision.pose.Pose, w: Int, h: Int) {
        val s = Settings(this)
        val names = mapOf(PoseLandmark.LEFT_HIP to "hip_l", PoseLandmark.RIGHT_HIP to "hip_r", PoseLandmark.LEFT_KNEE to "knee_l",
            PoseLandmark.RIGHT_KNEE to "knee_r", PoseLandmark.LEFT_ANKLE to "ank_l", PoseLandmark.RIGHT_ANKLE to "ank_r",
            PoseLandmark.LEFT_FOOT_INDEX to "toe_l", PoseLandmark.RIGHT_FOOT_INDEX to "toe_r", PoseLandmark.LEFT_SHOULDER to "sh_l",
            PoseLandmark.RIGHT_SHOULDER to "sh_r", PoseLandmark.LEFT_ELBOW to "el_l", PoseLandmark.RIGHT_ELBOW to "el_r",
            PoseLandmark.LEFT_EAR to "ear_l", PoseLandmark.RIGHT_EAR to "ear_r", PoseLandmark.NOSE to "nose")
        val pts = HashMap<String, FloatArray>()
        for ((type, name) in names) {
            val lm = pose.getPoseLandmark(type) ?: continue
            if (lm.inFrameLikelihood < 0.5f) continue
            val p = lm.position3D
            pts[name] = floatArrayOf(p.x, p.y, p.z)      // raw camera frames aren't mirrored (front or back)
        }
        val m = math ?: PoseMath(s.trackHeight).also { math = it }
        if (recalibrate) { if (m.calibrate(pts)) { recalibrate = false; status = "calibrated!! now calibrate FBT in VRChat :3" } }
        val res = m.trackers(pts, s.trackFull)
        if (res == null) { if (pts.size < 6) status = "can't see ur body ~ step back so ur feet are in view"; return }
        val code = s.remoteCode; val ip = RemoteLink.questIp.ifEmpty { s.remoteIp }
        if (ip.isEmpty() || code.isEmpty()) { status = "pair with ur Quest in the Remote tab first"; return }
        try {
            val sk = sock ?: DatagramSocket().also { sock = it }
            val addr = InetAddress.getByName(ip)
            for (msg in Trackers.messages(res.first, res.second, null)) {
                val b = TrackRelay.wrap(code, msg)
                sk.send(DatagramPacket(b, b.size, addr, TrackRelay.PORT))
            }
            frames++
            val now = System.currentTimeMillis()
            if (now - rateT >= 1000) { fps = frames * 1000f / (now - rateT); frames = 0; rateT = now }
            if (!status.startsWith("calibrated")) status = "tracking :3 · ${fps.toInt()} fps → $ip"
            last = res.first
        } catch (e: Exception) { status = "couldn't reach ur Quest (${e.message})" }
    }

    private fun notification(): Notification {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel("tracker", "Body tracker", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, "tracker").setContentTitle("Fluff VR Stats :3")
            .setContentText("camera body tracking is on").setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(open).setOngoing(true).build()
    }

    override fun onDestroy() {
        running = false
        status = "off"
        try { session?.close() } catch (_: Exception) {}
        try { camera?.close() } catch (_: Exception) {}
        try { reader?.close() } catch (_: Exception) {}
        try { detector.close() } catch (_: Exception) {}
        sock?.close()
        thread.quitSafely()
        super.onDestroy()
    }

    companion object {
        @Volatile var running = false
        @Volatile var status = "off"
        @Volatile var fps = 0f
        @Volatile var last: Map<String, FloatArray> = emptyMap()
        @Volatile var recalibrate = true
        @Volatile var rotation = 90

        fun start(ctx: Context) { recalibrate = true; ctx.startForegroundService(Intent(ctx, TrackerService::class.java)) }
        fun stop(ctx: Context) = ctx.stopService(Intent(ctx, TrackerService::class.java))
        fun calibrate() { recalibrate = true }
    }
}
