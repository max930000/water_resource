package tw.townquest.api.repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import tw.townquest.api.domain.Report;
import tw.townquest.api.domain.ReportStatus;

/**
 * 回報的資料存取。
 *
 * 回報的 JSON 需要 station_name，所以大部分查詢都加上
 * @EntityGraph(attributePaths = "station")：查回報時用 JOIN 把站點一起撈回來。
 * 這就是 FastAPI 版 selectinload(Report.station) 的角色 ——
 * 不加的話，每一筆回報讀 station 名稱時都會多發一次查詢（N+1）。
 */
public interface ReportRepository extends JpaRepository<Report, Integer>, JpaSpecificationExecutor<Report> {

    @EntityGraph(attributePaths = "station")
    List<Report> findByStationId(Integer stationId, Sort sort);

    @Override
    @EntityGraph(attributePaths = "station")
    Page<Report> findAll(Specification<Report> spec, Pageable pageable);

    @EntityGraph(attributePaths = "station")
    Optional<Report> findWithStationById(Integer id);

    /**
     * 一次算出這批站點各有幾筆指定狀態的回報。
     *
     * 一句 GROUP BY 解決，不管幾座站都只有 1 次查詢。
     * 回傳的每一列是 [stationId, count]。
     */
    @Query("""
            SELECT r.station.id, COUNT(r)
            FROM Report r
            WHERE r.station.id IN :stationIds AND r.status = :status
            GROUP BY r.station.id
            """)
    List<Object[]> countByStationIdsAndStatus(
            @Param("stationIds") Collection<Integer> stationIds,
            @Param("status") ReportStatus status);
}
