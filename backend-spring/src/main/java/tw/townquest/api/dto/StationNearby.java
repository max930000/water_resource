package tw.townquest.api.dto;

import com.fasterxml.jackson.annotation.JsonUnwrapped;

/**
 * 「附近」查詢的結果，比 Summary 多一個距離欄位。
 *
 * distance_meters 是依使用者位置「算出來」的，資料庫裡不存在 ——
 * 這正好說明為什麼 DTO 和 Entity 要分開。
 */
public record StationNearby(
        @JsonUnwrapped StationSummary summary,
        double distanceMeters) {
}
