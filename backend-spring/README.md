# TownQuest API —— Spring Boot 版

跟 [`backend/`](../backend)（FastAPI）提供**完全相同的 REST API**，共用同一個 PostgreSQL 與 Vue 前端。前端只要把 `VITE_API_BASE` 從 `:8000` 換成 `:8081`，一行程式碼都不用改。

做這個版本的目的，是用同一套需求比較兩種後端框架的設計差異。

## 技術

Java 25、Spring Boot 4.1、Spring Web MVC、Spring Data JPA（Hibernate）、Bean Validation、PostgreSQL、JUnit 5、Maven、Docker

## 啟動

**用 Docker（推薦）**：在專案根目錄執行 `docker compose up -d --build`，Spring 版會在 http://localhost:8081 啟動。

**本機開發**：需要先有一個已經跑過 Alembic migration 的 PostgreSQL（Spring 版不建表，見下方「資料表由誰管理」）。

```bash
cd backend-spring
./mvnw spring-boot:run        # Windows：mvnw.cmd spring-boot:run
./mvnw test                   # 執行單元測試
```

不用另外安裝 Maven，`mvnw` 會自動下載。

## 分層架構

```
HTTP 請求
   │
   ▼
web/          Controller   對應網址、驗證參數、呼叫 Service      ← @RestController
   │
   ▼
service/      Service      商業邏輯、交易範圍                    ← @Service @Transactional
   │
   ▼
repository/   Repository   資料存取（Spring Data JPA 自動實作）   ← interface
   │
   ▼
domain/       Entity       對應資料表                            ← @Entity
```

`dto/` 放 API 的輸入輸出格式，`config/` 放 CORS 設定。

## 跟 FastAPI 版的對照

| 概念 | FastAPI 版 | Spring Boot 版 |
|---|---|---|
| 路由 | `@app.get("/api/v1/stations")` | `@GetMapping` 在 `StationController` |
| 參數驗證 | `Query(ge=0, le=200)` | `@Min(0) @Max(200)` |
| Body 驗證 | Pydantic `ReportCreate` | `record ReportCreate` + `@Valid` |
| 資料表對應 | SQLAlchemy `models.py` | JPA `@Entity`（`domain/`） |
| API 格式 | Pydantic `schemas.py` | `record` DTO（`dto/`） |
| 查詢 | 每個查詢自己寫 `select(...)` | Repository 方法名稱自動產生 SQL、`Specification` 組動態條件 |
| 避免 N+1 | `selectinload(Report.station)` | `@EntityGraph(attributePaths = "station")` |
| 依賴注入 | `Depends(get_db)`，每個請求注入 | 建構子注入，啟動時注入一次 |
| 交易 | 手動 `db.commit()` | `@Transactional`，方法結束自動 commit、例外自動 rollback |
| 更新資料 | 改屬性後 `db.commit()` | 改屬性即可，dirty checking 自動 UPDATE |
| 錯誤處理 | `raise HTTPException(404)` | `throw ApiException.notFound(...)`，由 `GlobalExceptionHandler` 統一轉 JSON |
| 程式組織 | 路由與邏輯在同一個函式 | Controller / Service / Repository 分層 |

## 設計決策

**資料表由誰管理**：資料表的建立與版本管理一律交給 FastAPI 版的 Alembic。Spring 設定 `ddl-auto=validate`，啟動時只檢查 Entity 與資料表是否一致、絕不改表；兩邊對資料表的認知一旦不同步，Spring 會直接啟動失敗，而不是默默寫錯資料。

**PATCH 要分得出「沒送」和「送了 null」**：`{"admin_note": null}` 是清空回覆，沒送 `admin_note` 是維持原樣。一般的 record 分不出兩者，所以 `ReportUpdate` 直接讀原始 JSON Map，用 `containsKey` 判斷，等同 FastAPI 版的 `exclude_unset=True`。

**業務規則放在 Entity 上**：「結案時自動蓋完成時間、重新開啟時清掉」寫在 `Report.changeStatus()`，不管從哪裡改狀態都不會漏掉。

**關掉 Open Session In View**：開著的話，JSON 序列化時仍可能觸發 lazy loading、偷偷查資料庫，N+1 會藏在看不到的地方。關掉之後，該查的資料一定要在 Service 的交易內查完。

**時間統一輸出臺北時區**：PostgreSQL 的 timestamptz 讀回來是 UTC，FastAPI 版輸出 `+08:00`。前端直接截字串顯示時間，所以輸出前轉成臺北時間，否則畫面會少 8 小時。

**與 FastAPI 版的差異**：站點詳情（`GET /api/v1/stations/{id}`）的 `open_report_count` 會實際計算；FastAPI 版在這支 API 固定回 0。

## 驗證方式

開發時把兩個版本接到同一份資料庫的副本，用腳本逐支比對回應：13 支查詢 API 的 JSON 內容、13 種錯誤情況的狀態碼，以及回報的完整生命週期（新增 → 回覆 → 結案 → 重新開啟），兩個版本結果一致。`GeoUtilsTest` 涵蓋 Haversine 距離與方框換算。
