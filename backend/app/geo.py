"""
經緯度計算。

純函式：不碰資料庫、不碰 FastAPI、沒有任何副作用。
這種檔案最好測試，也最好重用 —— 之後做「回報熱點分析」還會用到。
"""

import math

# 地球平均半徑（公尺）
EARTH_RADIUS_M = 6_371_000.0

# 緯度 1 度對應的距離。各地幾乎相同（約 111.32 公里），
# 因為緯線之間的間隔不隨位置改變。
METERS_PER_LAT_DEGREE = 111_320.0


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    用 Haversine 公式算兩點在地球表面的距離（公尺）。

    為什麼不能用畢氏定理 √(Δlat² + Δlon²)？
      因為經緯度是「角度」不是「距離」，而且地球是球面。
      在臺北，緯度差 1 度約 111 公里，但經度差 1 度只有約 101 公里
      （越靠近極地差距越大，到北極時經度差 1 度等於 0 公尺）。
      直接套畢氏定理算出來的是「角度空間的距離」，沒有物理意義。

    Haversine 專門處理球面上的最短距離（大圓距離），
    在幾百公尺到幾百公里的尺度都夠準（誤差 < 0.5%）。
    """
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    # atan2 而不是 asin：數值上更穩定，兩點幾乎重合時不會出現精度問題
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def lat_delta(meters: float) -> float:
    """把「半徑幾公尺」換算成「緯度要加減多少度」。"""
    return meters / METERS_PER_LAT_DEGREE


def lon_delta(meters: float, at_lat: float) -> float:
    """
    把「半徑幾公尺」換算成「經度要加減多少度」。

    關鍵：經線在南北極會交會，所以緯度越高，經度 1 度越短。
    要除以 cos(緯度) 來補償。

    在臺北（緯度 25 度）cos(25°) ≈ 0.906，
    所以同樣 1000 公尺，經度要多加約 10% 的角度。
    漏掉這個 cos，東西向的搜尋範圍會少 10%，邊緣的點就查不到。

    max(scale, 0.01) 是防呆：接近極地時 cos 趨近 0，會變成除以零。
    """
    scale = math.cos(math.radians(at_lat))
    return meters / (METERS_PER_LAT_DEGREE * max(scale, 0.01))
