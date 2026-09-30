package tw.townquest.api.web;

import org.springframework.http.HttpStatus;

/**
 * 商業邏輯中「預期會發生」的錯誤，例如找不到站點、請求內容不合理。
 *
 * 等於 FastAPI 版的 raise HTTPException(status_code=404, detail="...")。
 * 丟出去之後由 GlobalExceptionHandler 統一轉成 {"detail": "..."} 的 JSON，
 * 格式跟 FastAPI 版一致，Vue 前端讀 detail 就能顯示錯誤訊息。
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;

    public ApiException(HttpStatus status, String detail) {
        super(detail);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }

    public static ApiException notFound(String detail) {
        return new ApiException(HttpStatus.NOT_FOUND, detail);
    }

    public static ApiException badRequest(String detail) {
        return new ApiException(HttpStatus.BAD_REQUEST, detail);
    }

    public static ApiException unprocessable(String detail) {
        return new ApiException(HttpStatus.UNPROCESSABLE_CONTENT, detail);
    }
}
