package tw.townquest.api.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * CORS：允許前端網頁呼叫這個 API。等於 FastAPI 版的 CORSMiddleware。
 *
 * 前端在 5173 / 8080、後端在 8081，port 不同 = 不同來源，
 * 不設定的話瀏覽器會直接擋下請求。
 * 允許的來源列出明確網址（從 app.cors-origins 讀），不用 "*"。
 */
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    private final String[] allowedOrigins;

    // @Value 從 application.properties（或環境變數）讀設定值，逗號分隔會自動轉成陣列
    public CorsConfig(@Value("${app.cors-origins}") String[] allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins(allowedOrigins)
                .allowedMethods("GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true);
    }
}
