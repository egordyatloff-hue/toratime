package org.example.toratime;

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;

import org.kivy.android.PythonActivity;
import org.json.JSONArray;

import java.util.Calendar;

public class AlarmReceiver extends BroadcastReceiver {

    public static final String ACTION_ALARM = "org.example.toratime.ALARM";
    public static final String PREFS_NAME = "toratime";
    public static final String KEY_SNAPSHOT = "alarm_snapshot";
    public static final String EXTRA_TITLE = "title";
    public static final String EXTRA_TEXT = "text";
    public static final String EXTRA_MINUTES = "minutes";
    private static final String CHANNEL_ID = "alarms";

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (ACTION_ALARM.equals(action)) {
            String text = intent.getStringExtra(EXTRA_TEXT);
            int minutes = intent.getIntExtra(EXTRA_MINUTES, -1);
            showNotification(context, text, minutes);
            if (minutes > 0) {
                schedule(context, minutes, text, tomorrowTrigger(minutes));
            }
        } else if (Intent.ACTION_BOOT_COMPLETED.equals(action)) {
            rescheduleAllFromSnapshot(context);
        }
    }

    protected static long nextTrigger(int minutes) {
        Calendar c = Calendar.getInstance();
        Calendar now = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, minutes / 60);
        c.set(Calendar.MINUTE, minutes % 60);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (!c.after(now)) {
            c.add(Calendar.DAY_OF_YEAR, 1);
        }
        return c.getTimeInMillis();
    }

    protected static long tomorrowTrigger(int minutes) {
        Calendar c = Calendar.getInstance();
        c.set(Calendar.HOUR_OF_DAY, minutes / 60);
        c.set(Calendar.MINUTE, minutes % 60);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        c.add(Calendar.DAY_OF_YEAR, 1);
        return c.getTimeInMillis();
    }

    protected static Intent buildIntent(Context context, int minutes, String msg) {
        Intent i = new Intent(context, AlarmReceiver.class);
        i.setAction(ACTION_ALARM);
        i.putExtra(EXTRA_TITLE, "Будильник");
        i.putExtra(EXTRA_TEXT, msg == null || msg.isEmpty() ? fmt(minutes) : msg);
        i.putExtra(EXTRA_MINUTES, minutes);
        return i;
    }

    protected static String fmt(int minutes) {
        return String.format(java.util.Locale.US, "%02d:%02d", minutes / 60, minutes % 60);
    }

    protected static void schedule(Context context, int minutes, String msg, long when) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            return;
        }
        Intent i = buildIntent(context, minutes, msg);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getBroadcast(context, minutes, i, flags);
        if (Build.VERSION.SDK_INT >= 31) {
            try {
                if (!am.canScheduleExactAlarms()) {
                    Log.d("AlarmReceiver", "exact alarms not allowed, skipping " + minutes);
                    return;
                }
            } catch (Throwable t) {
                return;
            }
        }
        try {
            AlarmManager.AlarmClockInfo info = new AlarmManager.AlarmClockInfo(when, null);
            am.setAlarmClock(info, pi);
            return;
        } catch (Throwable t) {
            // fallback below
        }
        am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, when, pi);
    }

    protected static void cancel(Context context, int minutes) {
        AlarmManager am = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (am == null) {
            return;
        }
        Intent i = buildIntent(context, minutes, "");
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getBroadcast(context, minutes, i, flags);
        am.cancel(pi);
    }

    protected static void showNotification(Context context, String text, int id) {
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) {
            return;
        }
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel ch = nm.getNotificationChannel(CHANNEL_ID);
            if (ch == null) {
                ch = new NotificationChannel(CHANNEL_ID, "Будильники",
                        NotificationManager.IMPORTANCE_HIGH);
                ch.enableVibration(true);
                ch.setSound(Settings.System.DEFAULT_ALARM_ALERT_URI,
                        android.media.AudioAttributes.newBuilder()
                                .setUsage(android.media.AudioAttributes.USAGE_ALARM)
                                .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                                .build());
                nm.createNotificationChannel(ch);
            }
        }
        Intent open = new Intent(context, PythonActivity.class);
        open.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= 23) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getActivity(context, id, open, flags);
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(context, CHANNEL_ID)
                : new Notification.Builder(context);
        b.setSmallIcon(android.R.drawable.ic_lock_alarm)
                .setContentTitle("Будильник")
                .setContentText(text == null ? "" : text)
                .setAutoCancel(true)
                .setContentIntent(pi)
                .setSound(Settings.System.DEFAULT_ALARM_ALERT_URI);
        if (Build.VERSION.SDK_INT >= 26) {
            b.setVibrate(new long[]{0, 700, 400, 700});
        } else {
            b.setPriority(Notification.PRIORITY_HIGH);
        }
        try {
            nm.notify(id, b.build());
        } catch (Throwable t) {
            Log.e("AlarmReceiver", "notify failed", t);
        }
    }

    protected static void rescheduleAllFromSnapshot(Context context) {
        Context c = context.getApplicationContext();
        SharedPreferences prefs = c.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String json = prefs.getString(KEY_SNAPSHOT, null);
        if (json == null || json.isEmpty()) {
            return;
        }
        try {
            JSONArray arr = new JSONArray(json);
            for (int i = 0; i < arr.length(); i++) {
                JSONArray e = arr.optJSONArray(i);
                if (e == null || e.length() < 2) {
                    continue;
                }
                int minutes = e.optInt(0, -1);
                String msg = e.optString(1, "");
                if (minutes < 0) {
                    continue;
                }
                schedule(c, minutes, msg, nextTrigger(minutes));
            }
        } catch (Throwable t) {
            Log.e("AlarmReceiver", "snapshot parse failed", t);
        }
    }
}