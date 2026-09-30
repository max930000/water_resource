package tw.townquest.api.dto;

import java.time.OffsetDateTime;
import java.time.ZoneId;

/**
 * 時間輸出格式。
 *
 * PostgreSQL 的 timestamptz 讀回來是 UTC（2026-09-21T06:09:01Z），
 * FastAPI 版則回傳臺北時間（2026-09-21T14:09:01+08:00）。
 * 兩者是同一個時間點，但 Vue 前端是直接截字串前 16 個字來顯示，
 * 回 UTC 的話畫面上會少 8 小時。所以輸出前統一轉成臺北時間。
 */
final class Times {

    private static final ZoneId TAIPEI = ZoneId.of("Asia/Taipei");

    private Times() {
    }

    static OffsetDateTime taipei(OffsetDateTime t) {
        return t == null ? null : t.atZoneSameInstant(TAIPEI).toOffsetDateTime();
    }
}
