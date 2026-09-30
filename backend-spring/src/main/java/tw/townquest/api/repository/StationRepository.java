package tw.townquest.api.repository;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import tw.townquest.api.domain.Station;

/**
 * 站點的資料存取。
 *
 * 這是 Spring Data JPA 最神奇的地方：只寫 interface，不用寫實作。
 *   - 繼承 JpaRepository → 自動有 findById、findAll、save、count…
 *   - 繼承 JpaSpecificationExecutor → 可以動態組查詢條件（列表篩選用）
 *   - 照命名規則寫方法名稱 → Spring 會「讀方法名稱」自動產生 SQL
 *
 * FastAPI 版每個查詢都要自己寫 select(Station).where(...)，
 * 這裡大部分查詢只要一個方法名稱就搞定。
 */
public interface StationRepository extends JpaRepository<Station, Integer>, JpaSpecificationExecutor<Station> {

    /**
     * 附近站點的「粗篩」：經緯度方框內的候選站點。
     *
     * 方法名稱會被翻譯成
     *   WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
     * 能吃到 Alembic 建的 idx_station_latlon 複合索引。
     */
    List<Station> findByLatBetweenAndLonBetween(double latMin, double latMax, double lonMin, double lonMax);

    /**
     * 不重複的 (縣市, 行政區) 組合，給行政區下拉選單用。
     *
     * 方法名稱表達不了 DISTINCT + 只取兩個欄位，所以用 @Query 寫 JPQL。
     * JPQL 長得像 SQL，但操作的是 Entity 和它的屬性（Station、s.city），不是表名和欄位名。
     */
    @Query("""
            SELECT DISTINCT s.city, s.district
            FROM Station s
            WHERE s.district IS NOT NULL
            ORDER BY s.city, s.district
            """)
    List<Object[]> findDistinctCityDistricts();
}
