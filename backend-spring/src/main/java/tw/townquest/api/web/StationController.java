package tw.townquest.api.web;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import tw.townquest.api.dto.DistrictGroup;
import tw.townquest.api.dto.PageResponse;
import tw.townquest.api.dto.StationDetail;
import tw.townquest.api.dto.StationNearby;
import tw.townquest.api.dto.StationSummary;
import tw.townquest.api.service.StationService;

/**
 * 站點 API。
 *
 * Controller 只做三件事：對應網址、驗證參數、呼叫 Service。
 * 不寫商業邏輯、不直接碰資料庫 —— 這就是分層的意義。
 *
 * @RestController = 這個類別的方法回傳值會自動轉成 JSON。
 * @GetMapping("...") = FastAPI 的 @app.get("...")。
 */
@RestController
@RequestMapping("/api/v1/stations")
public class StationController {

    private final StationService service;

    public StationController(StationService service) {
        this.service = service;
    }

    /**
     * 分頁查詢直飲臺。
     *
     * @Min / @Max 等於 FastAPI 的 Query(ge=..., le=...)。
     * size 上限 200 是保護措施：不讓別人用 size=999999 一次把整個資料庫拖走。
     */
    @GetMapping
    public PageResponse<StationSummary> list(
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String district,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(200) int size) {
        return service.list(city, district, keyword, page, size);
    }

    /**
     * 行政區清單。
     *
     * FastAPI 版要特別把這支寫在 /{station_id} 上面，否則 "districts" 會被當成 id。
     * Spring 會優先比對「固定字串」的路徑，所以不用管宣告順序 ——
     * 而且 /{id} 限定只接數字（見下方的 {id:\\d+}），兩者不會混淆。
     */
    @GetMapping("/districts")
    public List<DistrictGroup> districts() {
        return service.districts();
    }

    /** 查詢指定座標附近的直飲臺，依距離由近到遠排序。 */
    @GetMapping("/nearby")
    public List<StationNearby> nearby(
            @RequestParam
            @DecimalMin(value = "-90", message = "必須介於 -90 到 90 之間")
            @DecimalMax(value = "90", message = "必須介於 -90 到 90 之間") double lat,
            @RequestParam
            @DecimalMin(value = "-180", message = "必須介於 -180 到 180 之間")
            @DecimalMax(value = "180", message = "必須介於 -180 到 180 之間") double lon,
            @RequestParam(defaultValue = "1000")
            @DecimalMin(value = "0", inclusive = false, message = "必須大於 0")
            @DecimalMax(value = "20000", message = "上限為 20000 公尺") double radius,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int limit) {
        return service.nearby(lat, lon, radius, limit);
    }

    /** 取得單一直飲臺的完整資訊。 */
    @GetMapping("/{id:\\d+}")
    public StationDetail get(@PathVariable int id) {
        return service.get(id);
    }
}
