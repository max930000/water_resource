package tw.townquest.api.dto;

import tw.townquest.api.domain.Station;

/**
 * 列表與地圖用的精簡版。對應 FastAPI 版 schemas.py 的 StationSummary。
 *
 * 為什麼不直接回傳 Station Entity？
 *   跟 FastAPI 版把 models.py 和 schemas.py 分開是同一個理由：
 *   資料庫長什麼樣 ≠ API 長什麼樣。改資料表不該直接打破前端，
 *   也不該不小心把內部欄位外洩出去。
 *
 * record 是 Java 16 之後的語法：一行宣告欄位，自動產生建構子、getter、equals。
 * 很適合這種「只裝資料、不會變」的 DTO（Data Transfer Object）。
 * JSON 欄位名稱會被轉成 snake_case（見 application.properties）。
 */
public record StationSummary(
        Integer id,
        String externalId,
        String name,
        String city,
        String district,
        String address,
        Double lat,
        Double lon,
        String status,
        // 這座站目前有幾筆「待處理」回報。不是資料庫欄位，每次查詢時算出來。
        long openReportCount) {

    public static StationSummary of(Station s, long openReportCount) {
        return new StationSummary(
                s.getId(), s.getExternalId(), s.getName(), s.getCity(), s.getDistrict(),
                s.getAddress(), s.getLat(), s.getLon(), s.getStatus(), openReportCount);
    }
}
