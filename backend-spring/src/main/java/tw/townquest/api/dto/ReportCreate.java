package tw.townquest.api.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import tw.townquest.api.domain.ReportType;

/**
 * 建立回報的「輸入」格式。
 *
 * ⚠ 輸入和輸出一定要分開：輸入只放「使用者有權決定」的欄位。
 * id、status、created_at 都由伺服器決定，所以不在這裡 ——
 * 使用者就算在 body 塞 "status": "RESOLVED" 也會被忽略，沒辦法自己把案件結案。
 *
 * @NotNull、@Size 是 Bean Validation，等於 Pydantic 的型別檢查和 Field(max_length=500)。
 * Controller 參數加上 @Valid 就會自動檢查，不合格直接回 422。
 */
public record ReportCreate(
        @NotNull(message = "請選擇回報種類") ReportType type,
        @Size(max = 500, message = "補充說明最多 500 字") String description) {
}
