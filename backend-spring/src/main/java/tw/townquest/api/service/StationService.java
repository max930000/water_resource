package tw.townquest.api.service;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tw.townquest.api.domain.ReportStatus;
import tw.townquest.api.domain.Station;
import tw.townquest.api.dto.DistrictGroup;
import tw.townquest.api.dto.PageResponse;
import tw.townquest.api.dto.StationDetail;
import tw.townquest.api.dto.StationNearby;
import tw.townquest.api.dto.StationSummary;
import tw.townquest.api.repository.ReportRepository;
import tw.townquest.api.repository.StationRepository;
import tw.townquest.api.web.ApiException;

/**
 * 站點相關的商業邏輯。
 *
 * @Transactional(readOnly = true)：這個類別的方法都只讀資料庫。
 * 標成唯讀，Hibernate 就不用追蹤物件有沒有被改（省記憶體），
 * 資料庫也能針對唯讀交易做最佳化。
 */
@Service
@Transactional(readOnly = true)
public class StationService {

    private final StationRepository stations;
    private final ReportRepository reports;

    /**
     * 建構子注入：Spring 看到建構子需要 StationRepository 和 ReportRepository，
     * 就會自動把建立好的物件傳進來。
     * 等於 FastAPI 版每個端點的 db: Session = Depends(get_db)，
     * 差別是 Spring 在程式啟動時就注入好一次，不是每個請求都注入。
     */
    public StationService(StationRepository stations, ReportRepository reports) {
        this.stations = stations;
        this.reports = reports;
    }

    /** 分頁查詢直飲臺，可用縣市、行政區、關鍵字篩選。 */
    public PageResponse<StationSummary> list(String city, String district, String keyword, int page, int size) {
        // Specification 是「可以組合的查詢條件」：有給才加，沒給就跳過。
        // 等於 FastAPI 版先收集 conditions list、最後 where(*conditions) 的寫法。
        Specification<Station> spec = Specification.unrestricted();
        if (hasText(city)) {
            spec = spec.and((root, q, cb) -> cb.equal(root.get("city"), city));
        }
        if (hasText(district)) {
            spec = spec.and((root, q, cb) -> cb.equal(root.get("district"), district));
        }
        if (hasText(keyword)) {
            // 名稱或地址符合（不分大小寫）。
            // JPA 一律用參數化查詢，使用者輸入 '; DROP TABLE station; -- 也不會出事。
            String pattern = "%" + keyword.toLowerCase() + "%";
            spec = spec.and((root, q, cb) -> cb.or(
                    cb.like(cb.lower(root.get("name")), pattern),
                    cb.like(cb.lower(root.get("address")), pattern)));
        }

        // 一定要有穩定的排序，不然分頁時資料會重複或漏掉。
        // PageRequest 會自動產生 OFFSET / LIMIT，並另外發一次 COUNT 查詢算總數。
        PageRequest pageable = PageRequest.of(page, size, Sort.by("city", "district", "name"));
        Page<Station> result = stations.findAll(spec, pageable);

        Map<Integer, Long> counts = openReportCounts(result.getContent().stream().map(Station::getId).toList());
        List<StationSummary> items = result.getContent().stream()
                .map(s -> StationSummary.of(s, counts.getOrDefault(s.getId(), 0L)))
                .toList();
        return PageResponse.of(result, items);
    }

    /** 行政區清單，依縣市分組。 */
    public List<DistrictGroup> districts() {
        // SQL 已經照 (city, district) 排好序，這裡依序分組即可。
        // LinkedHashMap 會保留放入的順序（一般的 HashMap 不保證順序）。
        Map<String, List<String>> grouped = new LinkedHashMap<>();
        for (Object[] row : stations.findDistinctCityDistricts()) {
            String city = row[0] == null ? "其他" : (String) row[0];
            grouped.computeIfAbsent(city, k -> new ArrayList<>()).add((String) row[1]);
        }
        return grouped.entrySet().stream()
                .map(e -> new DistrictGroup(e.getKey(), e.getValue()))
                .toList();
    }

    /**
     * 查詢指定座標附近的直飲臺，依距離由近到遠排序。
     *
     * 做法跟 FastAPI 版一樣是「先粗篩再精算」：
     *   1. 用經緯度方框在資料庫篩出候選（走 idx_station_latlon 索引）
     *   2. 在 Java 裡用 Haversine 算精確距離、過濾、排序
     * 不在 SQL 裡對每一筆算三角函式，是因為那會讓索引失效、變成全表掃描。
     */
    public List<StationNearby> nearby(double lat, double lon, double radius, int limit) {
        // 步驟 1：方框粗篩
        double dLat = GeoUtils.latDelta(radius);
        double dLon = GeoUtils.lonDelta(radius, lat);
        List<Station> candidates = stations.findByLatBetweenAndLonBetween(
                lat - dLat, lat + dLat, lon - dLon, lon + dLon);

        // 步驟 2：精算距離、剔除方框四個角落超出半徑的點、排序、取前 limit 筆
        record Ranked(Station station, double distance) {
        }
        List<Ranked> top = candidates.stream()
                .map(s -> new Ranked(s, GeoUtils.distanceMeters(lat, lon, s.getLat(), s.getLon())))
                .filter(r -> r.distance() <= radius)
                .sorted(Comparator.comparingDouble(Ranked::distance))
                .limit(limit)
                .toList();

        Map<Integer, Long> counts = openReportCounts(top.stream().map(r -> r.station().getId()).toList());
        return top.stream()
                .map(r -> new StationNearby(
                        StationSummary.of(r.station(), counts.getOrDefault(r.station().getId(), 0L)),
                        Math.round(r.distance() * 10) / 10.0))
                .toList();
    }

    /** 取得單一直飲臺的完整資訊。 */
    public StationDetail get(int id) {
        // findById 回傳 Optional：「可能有、可能沒有」。
        // orElseThrow 在沒有的時候丟出 404，不回 200 加一個 null。
        Station station = stations.findById(id)
                .orElseThrow(() -> ApiException.notFound("找不到這座直飲臺"));
        long openCount = openReportCounts(List.of(id)).getOrDefault(id, 0L);
        return StationDetail.of(station, openCount);
    }

    /** 一次算出這批站點各有幾筆待處理回報（1 次 GROUP BY 查詢，不是 N 次）。 */
    private Map<Integer, Long> openReportCounts(Collection<Integer> stationIds) {
        Map<Integer, Long> counts = new HashMap<>();
        if (stationIds.isEmpty()) {
            return counts;
        }
        for (Object[] row : reports.countByStationIdsAndStatus(stationIds, ReportStatus.OPEN)) {
            counts.put((Integer) row[0], (Long) row[1]);
        }
        return counts;
    }

    private static boolean hasText(String s) {
        return s != null && !s.isBlank();
    }
}
