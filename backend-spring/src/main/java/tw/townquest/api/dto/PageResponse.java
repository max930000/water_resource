package tw.townquest.api.dto;

import java.util.List;
import org.springframework.data.domain.Page;

/**
 * 分頁結果的統一格式，對應 FastAPI 版的 StationPage / ReportPage。
 *
 * 不直接回傳 Spring 的 Page 物件：它的 JSON 格式會隨 Spring 版本改變，
 * 而且欄位名稱跟 FastAPI 版不同。自己定義格式，前端契約才穩定。
 *
 * &lt;T&gt; 是泛型：同一個類別可以裝站點，也可以裝回報，
 * 不用像 FastAPI 版那樣寫 StationPage、ReportPage 兩份。
 */
public record PageResponse<T>(List<T> items, int page, int size, long total, int totalPages) {

    public static <T> PageResponse<T> of(Page<?> page, List<T> items) {
        return new PageResponse<>(items, page.getNumber(), page.getSize(),
                page.getTotalElements(), page.getTotalPages());
    }
}
