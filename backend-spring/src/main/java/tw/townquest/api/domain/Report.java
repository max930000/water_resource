package tw.townquest.api.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import org.hibernate.annotations.Generated;
import org.hibernate.generator.EventType;

/** 市民對某座直飲臺的回報。對應 FastAPI 版 models.py 的 Report。 */
@Entity
@Table(name = "report")
public class Report {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    // 多筆回報屬於同一座站 → @ManyToOne，等於 SQLAlchemy 的 relationship()。
    //
    // ⚠ FetchType.LAZY：查回報時「不要」順便把站點撈回來，用到才查。
    // JPA 對 @ManyToOne 的預設是 EAGER，查 20 筆回報會連帶發 20 次站點查詢（N+1）。
    // 需要站點名稱的查詢，在 Repository 用 @EntityGraph 一次撈齊（= selectinload）。
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "station_id", nullable = false)
    private Station station;

    // EnumType.STRING：存 "BROKEN" 這種字串，不是存 0、1、2 的序號。
    // 存序號的話，哪天在 enum 中間插一個新值，資料庫裡的舊資料意義就全錯了。
    // 而且 FastAPI 版存的就是字串，兩邊必須一致。
    @Enumerated(EnumType.STRING)
    @Column(length = 20, nullable = false)
    private ReportType type;

    @Column(length = 500)
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(length = 20, nullable = false)
    private ReportStatus status = ReportStatus.OPEN;

    @Column(name = "admin_note", length = 500)
    private String adminNote;

    // 建立時間由資料庫的 CURRENT_TIMESTAMP 填（跟 FastAPI 版的 server_default 一樣）。
    // insertable = false：INSERT 時不送這個欄位，讓資料庫的預設值生效。
    // @Generated(INSERT)：INSERT 完之後 Hibernate 自動把資料庫填好的值讀回來 ——
    // 等於 FastAPI 版 create_report 裡的 db.refresh(report)。
    @Generated(event = EventType.INSERT)
    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "resolved_at")
    private OffsetDateTime resolvedAt;

    protected Report() {
    }

    public Report(Station station, ReportType type, String description) {
        this.station = station;
        this.type = type;
        this.description = description;
    }

    /**
     * 變更處理狀態。
     *
     * 業務規則：結案時自動蓋完成時間，重新開啟時清掉。
     * 規則寫在 Entity 自己身上，而不是散落在各個呼叫的地方 ——
     * 這樣不管從哪裡改狀態，都不可能忘記處理 resolvedAt。
     */
    public void changeStatus(ReportStatus newStatus) {
        this.status = newStatus;
        this.resolvedAt = newStatus.isClosed() ? OffsetDateTime.now() : null;
    }

    public void setAdminNote(String adminNote) {
        this.adminNote = adminNote;
    }

    public Integer getId() { return id; }
    public Station getStation() { return station; }
    public ReportType getType() { return type; }
    public String getDescription() { return description; }
    public ReportStatus getStatus() { return status; }
    public String getAdminNote() { return adminNote; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public OffsetDateTime getResolvedAt() { return resolvedAt; }
}
