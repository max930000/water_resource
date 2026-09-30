package tw.townquest.api.domain;

/** 回報的種類。字串值必須跟 FastAPI 版的 ReportType 完全一致，因為兩邊共用同一張表。 */
public enum ReportType {
    BROKEN,     // 設備故障
    NO_WATER,   // 沒有出水
    DIRTY,      // 環境髒污
    GOOD,       // 狀況良好
    OTHER
}
