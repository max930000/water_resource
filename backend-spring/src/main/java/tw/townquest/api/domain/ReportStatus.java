package tw.townquest.api.domain;

/** 回報的處理狀態，對應維護單位的實際工作流程。 */
public enum ReportStatus {
    OPEN,          // 待處理
    IN_PROGRESS,   // 處理中
    RESOLVED,      // 已完成
    REJECTED;      // 不受理

    /** 已結案（完成或不受理）。結案時要自動蓋完成時間。 */
    public boolean isClosed() {
        return this == RESOLVED || this == REJECTED;
    }
}
