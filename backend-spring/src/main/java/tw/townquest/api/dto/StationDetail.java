package tw.townquest.api.dto;

import com.fasterxml.jackson.annotation.JsonUnwrapped;
import java.time.OffsetDateTime;
import tw.townquest.api.domain.Station;

/**
 * 詳情頁用的完整版。
 *
 * FastAPI 版用「繼承」StationSummary 來重用共同欄位；record 不能繼承，
 * 所以改用「組合」：把 summary 包進來，再用 @JsonUnwrapped 攤平。
 * 輸出的 JSON 跟 FastAPI 版一模一樣，是一層平的物件，不會多一層 "summary": {...}。
 */
public record StationDetail(
        @JsonUnwrapped StationSummary summary,
        String placeType,
        String ownerUnit,
        String installSpot,
        String openHours,
        String maintainer,
        String phone,
        OffsetDateTime statusChangedAt,
        OffsetDateTime lastSampledAt,
        String coliform,
        String qualityUrl,
        String photoUrl,
        OffsetDateTime syncedAt) {

    public static StationDetail of(Station s, long openReportCount) {
        return new StationDetail(
                StationSummary.of(s, openReportCount),
                s.getPlaceType(), s.getOwnerUnit(), s.getInstallSpot(), s.getOpenHours(),
                s.getMaintainer(), s.getPhone(), Times.taipei(s.getStatusChangedAt()), Times.taipei(s.getLastSampledAt()),
                s.getColiform(), s.getQualityUrl(), s.getPhotoUrl(), Times.taipei(s.getSyncedAt()));
    }
}
