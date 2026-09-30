package tw.townquest.api.dto;

import java.time.OffsetDateTime;
import tw.townquest.api.domain.Report;
import tw.townquest.api.domain.ReportStatus;
import tw.townquest.api.domain.ReportType;

/** 回報的「輸出」格式，比輸入多了伺服器決定的欄位。 */
public record ReportOut(
        Integer id,
        Integer stationId,
        String stationName,
        ReportType type,
        String description,
        ReportStatus status,
        String adminNote,
        OffsetDateTime createdAt,
        OffsetDateTime resolvedAt) {

    /** ⚠ 呼叫前 report.getStation() 必須已經載入（Repository 用 @EntityGraph），否則會 N+1。 */
    public static ReportOut of(Report r) {
        return new ReportOut(
                r.getId(), r.getStation().getId(), r.getStation().getName(),
                r.getType(), r.getDescription(), r.getStatus(), r.getAdminNote(),
                Times.taipei(r.getCreatedAt()), Times.taipei(r.getResolvedAt()));
    }
}
