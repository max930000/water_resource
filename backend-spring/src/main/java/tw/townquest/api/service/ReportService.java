package tw.townquest.api.service;

import jakarta.persistence.criteria.Join;
import java.util.List;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tw.townquest.api.domain.Report;
import tw.townquest.api.domain.ReportStatus;
import tw.townquest.api.domain.Station;
import tw.townquest.api.dto.PageResponse;
import tw.townquest.api.dto.ReportCreate;
import tw.townquest.api.dto.ReportOut;
import tw.townquest.api.dto.ReportUpdate;
import tw.townquest.api.repository.ReportRepository;
import tw.townquest.api.repository.StationRepository;
import tw.townquest.api.web.ApiException;

/** 市民回報相關的商業邏輯。 */
@Service
@Transactional(readOnly = true)
public class ReportService {

    // ⚠ 排序一定要加 id 當最後一個鍵（tiebreaker）。
    // 同一秒內建立的回報 created_at 可能相同，資料庫不保證它們的順序，
    // 分頁時會出現「同一筆出現在兩頁」或「某筆永遠看不到」。
    private static final Sort NEWEST_FIRST = Sort.by(
            Sort.Order.desc("createdAt"), Sort.Order.desc("id"));

    private final ReportRepository reports;
    private final StationRepository stations;

    public ReportService(ReportRepository reports, StationRepository stations) {
        this.reports = reports;
        this.stations = stations;
    }

    /**
     * 新增一筆市民回報。
     *
     * 這個方法要寫入資料庫，所以覆蓋掉類別上的 readOnly，改成一般的交易。
     * 方法正常結束 → 自動 commit；中途丟出例外 → 自動 rollback。
     * 不用像 FastAPI 版那樣自己呼叫 db.commit()。
     */
    @Transactional
    public ReportOut create(int stationId, ReportCreate payload) {
        // 先確認站點存在。不檢查的話，外鍵約束會在寫入時失敗、前端收到 500 ——
        // 但這其實是使用者給錯 id，應該回 404。狀態碼要說實話。
        Station station = stations.findById(stationId)
                .orElseThrow(() -> ApiException.notFound("找不到這座直飲臺"));

        Report report = reports.save(new Report(station, payload.type(), payload.description()));
        return ReportOut.of(report);
    }

    /** 某一座直飲臺的所有回報，新的在前。 */
    public List<ReportOut> listByStation(int stationId) {
        if (!stations.existsById(stationId)) {
            throw ApiException.notFound("找不到這座直飲臺");
        }
        return reports.findByStationId(stationId, NEWEST_FIRST).stream()
                .map(ReportOut::of)
                .toList();
    }

    /** 所有回報的列表，給維護單位後台用。 */
    public PageResponse<ReportOut> list(ReportStatus status, String city, String district, int page, int size) {
        Specification<Report> spec = Specification.unrestricted();
        if (status != null) {
            spec = spec.and((root, q, cb) -> cb.equal(root.get("status"), status));
        }
        // 縣市和行政區在 station 表上，要 join 過去才篩得到
        if (hasText(city)) {
            spec = spec.and((root, q, cb) -> {
                Join<Report, Station> s = root.join("station");
                return cb.equal(s.get("city"), city);
            });
        }
        if (hasText(district)) {
            spec = spec.and((root, q, cb) -> {
                Join<Report, Station> s = root.join("station");
                return cb.equal(s.get("district"), district);
            });
        }

        Page<Report> result = reports.findAll(spec, PageRequest.of(page, size, NEWEST_FIRST));
        return PageResponse.of(result, result.getContent().stream().map(ReportOut::of).toList());
    }

    /** 取得單一回報 —— 讓市民查自己那筆的處理進度。 */
    public ReportOut get(int reportId) {
        return reports.findWithStationById(reportId)
                .map(ReportOut::of)
                .orElseThrow(() -> ApiException.notFound("找不到這筆回報"));
    }

    /**
     * 更新回報的處理狀態與回覆（維護單位用）。
     *
     * ⚠ 目前沒有權限控管，任何人都打得到。正式版要接身分驗證 + 角色授權。
     *
     * 注意這裡沒有呼叫 save()：在交易裡從資料庫讀出來的 Entity 是「被追蹤」的，
     * 改了它的欄位，交易結束時 Hibernate 會自動產生 UPDATE（dirty checking）。
     */
    @Transactional
    public ReportOut update(int reportId, ReportUpdate changes) {
        Report report = reports.findWithStationById(reportId)
                .orElseThrow(() -> ApiException.notFound("找不到這筆回報"));

        if (changes.isEmpty()) {
            throw ApiException.badRequest("沒有提供任何要更新的欄位");
        }
        if (changes.hasStatus()) {
            // 結案時自動蓋完成時間、重新開啟時清掉 —— 規則寫在 Report.changeStatus 裡
            report.changeStatus(changes.status());
        }
        if (changes.hasAdminNote()) {
            report.setAdminNote(changes.adminNote());
        }
        return ReportOut.of(report);
    }

    private static boolean hasText(String s) {
        return s != null && !s.isBlank();
    }
}
