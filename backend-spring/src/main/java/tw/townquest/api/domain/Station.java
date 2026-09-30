package tw.townquest.api.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

/**
 * 直飲臺。對應 FastAPI 版 models.py 的 Station。
 *
 * @Entity = SQLAlchemy 的 class Station(Base)：一個類別對應一張表。
 * 欄位長度要跟 Alembic 建的表一致，否則啟動時 ddl-auto=validate 會直接報錯 ——
 * 這正是 validate 的用意：兩個後端對資料表的認知一旦不同步，馬上就知道。
 *
 * 這個類別只有 getter 沒有 setter：站點資料只由開放資料同步寫入（Python 版的 app.sync），
 * API 本身只會讀，不讓 Java 這邊有機會改到它。
 */
@Entity
@Table(name = "station")
public class Station {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    // 臺北市開放資料的「直飲臺編號」，同步時用它比對同一座站
    @Column(name = "external_id", length = 32, nullable = false, unique = true)
    private String externalId;

    @Column(length = 200, nullable = false)
    private String name;

    @Column(length = 300)
    private String address;

    @Column(length = 20)
    private String city;

    @Column(length = 20)
    private String district;

    @Column(name = "place_type", length = 50)
    private String placeType;

    @Column(name = "owner_unit", length = 200)
    private String ownerUnit;

    @Column(name = "install_spot", length = 300)
    private String installSpot;

    @Column(name = "open_hours", length = 100)
    private String openHours;

    @Column(nullable = false)
    private Double lon;

    @Column(nullable = false)
    private Double lat;

    @Column(length = 200)
    private String maintainer;

    @Column(length = 50)
    private String phone;

    @Column(length = 30)
    private String status;

    @Column(name = "status_changed_at")
    private OffsetDateTime statusChangedAt;

    @Column(name = "last_sampled_at")
    private OffsetDateTime lastSampledAt;

    @Column(length = 30)
    private String coliform;

    @Column(name = "quality_url", length = 500)
    private String qualityUrl;

    @Column(name = "photo_url", length = 500)
    private String photoUrl;

    @Column(name = "synced_at", nullable = false)
    private OffsetDateTime syncedAt;

    // JPA 規定要有無參數建構子（Hibernate 用它建立物件再填欄位）。
    // protected 讓外部程式碼不能隨手 new 一個空的 Station。
    protected Station() {
    }

    public Integer getId() { return id; }
    public String getExternalId() { return externalId; }
    public String getName() { return name; }
    public String getAddress() { return address; }
    public String getCity() { return city; }
    public String getDistrict() { return district; }
    public String getPlaceType() { return placeType; }
    public String getOwnerUnit() { return ownerUnit; }
    public String getInstallSpot() { return installSpot; }
    public String getOpenHours() { return openHours; }
    public Double getLon() { return lon; }
    public Double getLat() { return lat; }
    public String getMaintainer() { return maintainer; }
    public String getPhone() { return phone; }
    public String getStatus() { return status; }
    public OffsetDateTime getStatusChangedAt() { return statusChangedAt; }
    public OffsetDateTime getLastSampledAt() { return lastSampledAt; }
    public String getColiform() { return coliform; }
    public String getQualityUrl() { return qualityUrl; }
    public String getPhotoUrl() { return photoUrl; }
    public OffsetDateTime getSyncedAt() { return syncedAt; }
}
