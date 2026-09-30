package tw.townquest.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * TownQuest API（Spring Boot 版）的入口。
 *
 * 跟 FastAPI 版的 app/main.py 做一樣的事，但分工方式不同：
 *   FastAPI 版把路由、查詢、商業邏輯都寫在同一個函式裡；
 *   Spring 版拆成三層，每一層只做一件事：
 *
 *     web/         Controller  —— 接 HTTP 請求、驗證參數、回傳 JSON
 *     service/     Service     —— 商業邏輯（例如「結案時自動蓋完成時間」）
 *     repository/  Repository  —— 跟資料庫講話
 *
 * @SpringBootApplication 會掃描這個 package 底下所有加了
 * @RestController、@Service、@Repository 的類別，自動建立物件並互相注入 ——
 * 這就是「依賴注入」，概念跟 FastAPI 的 Depends(get_db) 相同。
 */
@SpringBootApplication
public class TownQuestApplication {

    public static void main(String[] args) {
        SpringApplication.run(TownQuestApplication.class, args);
    }
}
