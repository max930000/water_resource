package tw.townquest.api.web;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

/**
 * 全域錯誤處理：把各種例外統一轉成 {"detail": "..."}。
 *
 * FastAPI 會自動把驗證錯誤轉成 422，Spring 預設則是回 400 加上 Spring 自己的格式。
 * 集中在這裡處理，所有 Controller 都不用各自 try/catch，
 * 錯誤格式也跟 FastAPI 版一致。
 *
 * 狀態碼的原則跟 FastAPI 版相同：
 *   404 —— 指定的資源不存在
 *   400 —— 請求本身不合理（例如 PATCH 什麼都沒送）
 *   422 —— 格式對不上（缺必填欄位、數值超出範圍、enum 值不存在）
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Map<String, String>> handleApi(ApiException e) {
        return detail(e.getStatus(), e.getMessage());
    }

    // @Valid 檢查 request body 失敗（例如 description 超過 500 字）
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, String>> handleBodyValidation(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(err -> err.getDefaultMessage())
                .orElse("請求內容驗證失敗");
        return detail(HttpStatus.UNPROCESSABLE_CONTENT, message);
    }

    // @RequestParam 上的 @Min / @Max 檢查失敗（例如 size=999）
    @ExceptionHandler(HandlerMethodValidationException.class)
    public ResponseEntity<Map<String, String>> handleParamValidation(HandlerMethodValidationException e) {
        String message = e.getParameterValidationResults().stream()
                .flatMap(r -> r.getResolvableErrors().stream()
                        .map(err -> r.getMethodParameter().getParameterName() + " " + err.getDefaultMessage()))
                .findFirst()
                .orElse("查詢參數驗證失敗");
        return detail(HttpStatus.UNPROCESSABLE_CONTENT, message);
    }

    // 型別轉不過去（例如 lat=abc、status=DONE）
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<Map<String, String>> handleTypeMismatch(MethodArgumentTypeMismatchException e) {
        return detail(HttpStatus.UNPROCESSABLE_CONTENT, "參數 " + e.getName() + " 的格式不正確");
    }

    // 必填的查詢參數沒給（例如 /nearby 沒帶 lat）
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<Map<String, String>> handleMissingParam(MissingServletRequestParameterException e) {
        return detail(HttpStatus.UNPROCESSABLE_CONTENT, "缺少必填參數 " + e.getParameterName());
    }

    // body 不是合法 JSON，或 enum 值不存在（例如 "type": "EXPLODED"）
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, String>> handleUnreadable(HttpMessageNotReadableException e) {
        return detail(HttpStatus.UNPROCESSABLE_CONTENT, "請求內容格式不正確");
    }

    private static ResponseEntity<Map<String, String>> detail(HttpStatus status, String message) {
        return ResponseEntity.status(status).body(Map.of("detail", message));
    }
}
