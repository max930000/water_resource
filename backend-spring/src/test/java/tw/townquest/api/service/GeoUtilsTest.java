package tw.townquest.api.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

/**
 * GeoUtils 的單元測試。
 *
 * 純函式不需要 Spring、不需要資料庫，測試跑起來不到一秒 ——
 * 這就是把計算邏輯拆成純函式的好處。
 */
class GeoUtilsTest {

    // 臺北車站、臺北 101 的座標
    private static final double TPE_STATION_LAT = 25.0478;
    private static final double TPE_STATION_LON = 121.5170;
    private static final double TAIPEI_101_LAT = 25.0340;
    private static final double TAIPEI_101_LON = 121.5645;

    @Test
    void 同一個點的距離是零() {
        assertThat(GeoUtils.distanceMeters(TPE_STATION_LAT, TPE_STATION_LON, TPE_STATION_LAT, TPE_STATION_LON))
                .isEqualTo(0.0);
    }

    @Test
    void 臺北車站到臺北101約五公里() {
        double d = GeoUtils.distanceMeters(TPE_STATION_LAT, TPE_STATION_LON, TAIPEI_101_LAT, TAIPEI_101_LON);
        assertThat(d).isCloseTo(5_000, within(300.0));
    }

    @Test
    void 距離與方向無關() {
        double there = GeoUtils.distanceMeters(TPE_STATION_LAT, TPE_STATION_LON, TAIPEI_101_LAT, TAIPEI_101_LON);
        double back = GeoUtils.distanceMeters(TAIPEI_101_LAT, TAIPEI_101_LON, TPE_STATION_LAT, TPE_STATION_LON);
        assertThat(there).isCloseTo(back, within(1e-6));
    }

    @Test
    void 緯度差一度約111公里() {
        assertThat(GeoUtils.distanceMeters(25.0, 121.5, 26.0, 121.5)).isCloseTo(111_195, within(100.0));
    }

    @Test
    void 在臺北經度方框要比緯度方框寬約百分之十() {
        // cos(25°) ≈ 0.906，所以同樣 1000 公尺，經度要多加約 10% 的角度
        double ratio = GeoUtils.lonDelta(1000, 25.0) / GeoUtils.latDelta(1000);
        assertThat(ratio).isCloseTo(1 / Math.cos(Math.toRadians(25.0)), within(1e-9));
        assertThat(ratio).isBetween(1.09, 1.11);
    }

    @Test
    void 方框一定包得住半徑內的點() {
        // 從臺北車站往正東走 1000 公尺，這個點必須落在 1000 公尺的方框內
        double radius = 1000;
        double east = TPE_STATION_LON + GeoUtils.lonDelta(radius, TPE_STATION_LAT) * 0.99;
        assertThat(GeoUtils.distanceMeters(TPE_STATION_LAT, TPE_STATION_LON, TPE_STATION_LAT, east))
                .isLessThanOrEqualTo(radius);
    }

    @Test
    void 接近極地時不會除以零() {
        assertThat(GeoUtils.lonDelta(1000, 90.0)).isFinite();
    }
}
