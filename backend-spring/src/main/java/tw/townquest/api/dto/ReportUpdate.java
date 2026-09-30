package tw.townquest.api.dto;

import java.util.Map;
import java.util.Set;
import tw.townquest.api.domain.ReportStatus;
import tw.townquest.api.web.ApiException;

/**
 * 更新回報的輸入格式（PATCH 用）。
 *
 * PATCH 的語意是「只改有送的欄位」，所以必須分得出三種情況：
 *   {"admin_note": "已派員"}   → 改回覆
 *   {"admin_note": null}       → 把回覆清空
 *   {}（沒送 admin_note）       → 回覆維持原樣
 * 一般的 record 分不出「沒送」跟「送了 null」（兩者都是 null），
 * 所以這裡直接讀原始的 JSON Map，用 containsKey 判斷有沒有送。
 * 這等於 FastAPI 版的 payload.model_dump(exclude_unset=True)。
 *
 * 只認 status 和 admin_note 兩個欄位，其他欄位（id、type、created_at…）一律忽略 ——
 * 使用者改不到不該改的東西。
 */
public record ReportUpdate(boolean hasStatus, ReportStatus status, boolean hasAdminNote, String adminNote) {

    private static final Set<String> STATUS_VALUES = Set.of(
            "OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED");

    public static ReportUpdate from(Map<String, Object> body) {
        if (body == null) {
            body = Map.of();
        }

        boolean hasStatus = body.containsKey("status");
        ReportStatus status = null;
        if (hasStatus) {
            Object raw = body.get("status");
            // status 在資料庫是 NOT NULL，送 null 過來是錯的請求，要回 422 而不是讓資料庫炸 500
            if (!(raw instanceof String s) || !STATUS_VALUES.contains(s)) {
                throw ApiException.unprocessable("status 必須是 OPEN、IN_PROGRESS、RESOLVED、REJECTED 其中之一");
            }
            status = ReportStatus.valueOf(s);
        }

        boolean hasAdminNote = body.containsKey("admin_note");
        String adminNote = null;
        if (hasAdminNote) {
            Object raw = body.get("admin_note");
            if (raw != null && !(raw instanceof String)) {
                throw ApiException.unprocessable("admin_note 必須是文字");
            }
            adminNote = (String) raw;
            if (adminNote != null && adminNote.length() > 500) {
                throw ApiException.unprocessable("處理說明最多 500 字");
            }
        }

        return new ReportUpdate(hasStatus, status, hasAdminNote, adminNote);
    }

    public boolean isEmpty() {
        return !hasStatus && !hasAdminNote;
    }
}
