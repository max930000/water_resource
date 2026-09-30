package tw.townquest.api.service;

/**
 * 經緯度計算。從 FastAPI 版的 app/geo.py 移植，邏輯完全相同。
 *
 * 純函式：不碰資料庫、不碰 Spring，沒有任何副作用 —— 最好測試，見 GeoUtilsTest。
 */
public final class GeoUtils {

    /** 地球平均半徑（公尺） */
    static final double EARTH_RADIUS_M = 6_371_000.0;

    /** 緯度 1 度對應的距離，各地幾乎相同（約 111.32 公里） */
    static final double METERS_PER_LAT_DEGREE = 111_320.0;

    private GeoUtils() {
        // 工具類別，不讓人 new
    }

    /**
     * 用 Haversine 公式算兩點在地球表面的距離（公尺）。
     *
     * 經緯度是「角度」不是「距離」，而且地球是球面，
     * 不能直接用畢氏定理 √(Δlat² + Δlon²)。
     */
    public static double distanceMeters(double lat1, double lon1, double lat2, double lon2) {
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);

        double a = Math.pow(Math.sin(dLat / 2), 2)
                + Math.cos(Math.toRadians(lat1))
                * Math.cos(Math.toRadians(lat2))
                * Math.pow(Math.sin(dLon / 2), 2);

        // atan2 而不是 asin：兩點幾乎重合時數值更穩定
        return EARTH_RADIUS_M * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    /** 把「半徑幾公尺」換算成「緯度要加減多少度」。 */
    public static double latDelta(double meters) {
        return meters / METERS_PER_LAT_DEGREE;
    }

    /**
     * 把「半徑幾公尺」換算成「經度要加減多少度」。
     *
     * 緯度越高，經度 1 度越短，要除以 cos(緯度) 補償。
     * Math.max(scale, 0.01) 防止接近極地時除以零。
     */
    public static double lonDelta(double meters, double atLat) {
        double scale = Math.cos(Math.toRadians(atLat));
        return meters / (METERS_PER_LAT_DEGREE * Math.max(scale, 0.01));
    }
}
