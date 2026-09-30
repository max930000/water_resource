package tw.townquest.api.web;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import tw.townquest.api.domain.ReportStatus;
import tw.townquest.api.dto.PageResponse;
import tw.townquest.api.dto.ReportCreate;
import tw.townquest.api.dto.ReportOut;
import tw.townquest.api.dto.ReportUpdate;
import tw.townquest.api.service.ReportService;

/** 市民回報 API。 */
@RestController
@RequestMapping("/api/v1")
public class ReportController {

    private final ReportService service;

    public ReportController(ReportService service) {
        this.service = service;
    }

    /**
     * 新增一筆市民回報。
     *
     * @RequestBody = 從 request body 的 JSON 讀進 ReportCreate。
     * @Valid = 依 ReportCreate 上的 @NotNull / @Size 檢查，不合格自動回 422。
     * @ResponseStatus(CREATED) = 成功回 201，不是 200 —— 新增資源成功的正確狀態碼。
     */
    @PostMapping("/stations/{stationId:\\d+}/reports")
    @ResponseStatus(HttpStatus.CREATED)
    public ReportOut create(@PathVariable int stationId, @Valid @RequestBody ReportCreate payload) {
        return service.create(stationId, payload);
    }

    /** 某一座直飲臺的所有回報，新的在前。 */
    @GetMapping("/stations/{stationId:\\d+}/reports")
    public List<ReportOut> listByStation(@PathVariable int stationId) {
        return service.listByStation(stationId);
    }

    /** 所有回報的列表，給維護單位後台用。 */
    @GetMapping("/reports")
    public PageResponse<ReportOut> list(
            @RequestParam(required = false) ReportStatus status,
            @RequestParam(required = false) String city,
            @RequestParam(required = false) String district,
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
        return service.list(status, city, district, page, size);
    }

    /** 取得單一回報。 */
    @GetMapping("/reports/{reportId:\\d+}")
    public ReportOut get(@PathVariable int reportId) {
        return service.get(reportId);
    }

    /**
     * 更新回報的處理狀態與回覆（維護單位用）。
     *
     * body 用 Map 接而不是 record，原因見 ReportUpdate 的說明（要分得出「沒送」和「送了 null」）。
     */
    @PatchMapping("/reports/{reportId:\\d+}")
    public ReportOut update(@PathVariable int reportId, @RequestBody(required = false) Map<String, Object> body) {
        return service.update(reportId, ReportUpdate.from(body));
    }
}
