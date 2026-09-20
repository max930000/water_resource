"""
data.taipei 開放資料存取。

這個檔案只負責「把外部資料抓回來、整理成乾淨的 Python dict」。
寫入資料庫是下一步（sync.py）的事。

資料來源：臺北市資料大平臺「臺北市所屬直飲臺」（臺北自來水事業處）
授權：政府資料開放授權條款第 1 版
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import ssl

# ── 資料來源 ────────────────────────────────────────────
BASE_URL = "https://data.taipei/api/v1/dataset"

# 注意：這是「資源 ID」(resource id)，不是「資料集 ID」(dataset id)。
# 一個資料集底下可能有多個資源（多個檔案），要用資源 ID 才抓得到實際資料。
RESOURCE_ID = "181097e0-c171-4bcd-ad41-c7b55dbc616e"

# 一次抓幾筆。太小會打太多次請求，太大對方可能拒絕。
PAGE_SIZE = 1000

# 臺灣沒有日光節約時間，所以固定 +08:00 就完全正確，
# 不需要 zoneinfo（那在 Windows 上還要額外裝 tzdata 套件）。
TAIPEI_TZ = timezone(timedelta(hours=8), "Asia/Taipei")


def _ssl_context() -> ssl.SSLContext:
    """
    建立 SSL 設定，處理 data.taipei 憑證的相容性問題。

    Python 3.13 起預設啟用 VERIFY_X509_STRICT，會嚴格按 RFC 5280
    檢查憑證的擴充欄位。data.taipei 憑證鏈裡有一張 CA 少了
    Subject Key Identifier，就被拒絕，錯誤訊息是：
        SSL: CERTIFICATE_VERIFY_FAILED: Missing Subject Key Identifier

    我們只移除這個「格式嚴格度」旗標，
    主機名稱驗證（check_hostname）和信任鏈驗證（CERT_REQUIRED）都保留。

    絕對不要改用 verify=False —— 那會完全停止驗證，等於自願被中間人攻擊。
    """
    ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx


def fetch_rows() -> list[dict[str, Any]]:
    """
    分頁把整份資料集抓完，回傳原始的 dict 清單（欄位名是中文）。

    回應結構：
        {"result": {"limit":1000, "offset":0, "count":739, "results":[{...}, ...]}}
    count 是總筆數，用它當迴圈的終止條件。
    """
    rows: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None

    # httpx.Client 用 with 包起來，離開時會自動關閉連線。
    # 重複使用同一個 client 可以沿用 TCP 連線，比每次 httpx.get() 快。
    with httpx.Client(verify=_ssl_context(), timeout=30) as client:
        while total is None or offset < total:
            response = client.get(
                f"{BASE_URL}/{RESOURCE_ID}",
                params={
                    # scope=resourceAquire 是固定要帶的，
                    # 不帶會拿到資料集的「描述」而不是資料本身
                    "scope": "resourceAquire",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                },
            )
            # 4xx / 5xx 直接丟例外，不要讓壞資料靜靜流進系統
            response.raise_for_status()

            result = response.json()["result"]
            batch = result.get("results", [])
            if not batch:
                break

            rows.extend(batch)
            total = result.get("count") or len(rows)

            # 關鍵：offset 要加「這次實際拿到幾筆」，不要加 PAGE_SIZE。
            # 最後一頁通常不滿，寫錯會變成無限迴圈或少抓資料。
            offset += len(batch)
            print(f"  已取得 {len(rows)}/{total} 筆")

    return rows


def _clean(value: Any) -> str | None:
    """
    把開放資料的值正規化成「乾淨的字串或 None」。

    政府開放資料的「沒有值」有很多種寫法：
    空字串、空白、"無"、"NA"、"-"。全部統一成 None，
    後面的程式就只要判斷一種情況。
    """
    if value is None:
        return None
    text = str(value).strip()
    if text in ("", "無", "NA", "N/A", "-", "null"):
        return None
    return text


def _to_float(value: Any) -> float | None:
    """字串轉浮點數，轉不動就回 None（而不是讓整批匯入失敗）。"""
    text = _clean(value)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_datetime(value: Any) -> datetime | None:
    """
    解析開放資料的時間格式：20211201T090000

    這不是標準 ISO 8601（少了分隔符號），所以 datetime.fromisoformat()
    解不動，要自己給格式字串。政府資料的時間格式幾乎沒有一致的，
    每接一份新資料都要先看清楚。
    """
    text = _clean(value)
    if text is None:
        return None
    try:
        naive = datetime.strptime(text, "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    # 補上時區資訊。沒有時區的時間（naive datetime）存進資料庫
    # 之後一定會出現「差 8 小時」的 bug。
    return naive.replace(tzinfo=TAIPEI_TZ)

def _normalize_district(value: Any) -> str | None:
    """
    統一行政區的寫法。

    來源資料同一個區有兩種寫法：「大安」57 筆、「大安區」3 筆。
    不統一的話，district=大安 的查詢會漏掉那 3 筆 ——
    使用者看不到那幾座直飲臺，而且不會有任何錯誤訊息。

    統一成「有區字」的版本（大安區），理由：
      1. 那是官方正式的行政區名稱
      2. data.taipei 其他資料集（公廁、公園、YouBike）多半也用這種寫法，
         之後要跨資料集做關聯時才對得起來
    """
    text = _clean(value)
    if text is None:
        return None
    return text if text.endswith("區") else f"{text}區"


def _resolve_city(row: dict[str, Any]) -> str | None:
    """
    修正縣市欄位。

    資料裡有 2 筆的「市別」標成臺北市，但地址明明在新北市新店區
    （2906 十四張公園、2906a 十四張公園）。

    地址是人工填寫的完整資訊，比「市別」這個下拉選單欄位可信，
    所以地址開頭如果寫明縣市，就以地址為準。

    這種「用比較可信的欄位去校正比較不可信的欄位」是資料清理的常見手法。
    """
    address = _clean(row.get("地址")) or ""
    for city in ("臺北市", "新北市", "台北市"):
        if address.startswith(city):
            # 「台」統一成「臺」，避免又多出一種寫法
            return city.replace("台", "臺")
    return _clean(row.get("市別"))


def to_station_dict(row: dict[str, Any]) -> dict[str, Any] | None:
    """
    把一筆開放資料（中文欄位名）對應成我們 Station model 的欄位。

    回傳 None 表示「這筆資料不能用」—— 缺了編號或座標，
    存進資料庫也沒意義。呼叫方要負責統計跳過了幾筆。
    """
    external_id = _clean(row.get("直飲臺編號"))
    lon = _to_float(row.get("經度"))
    lat = _to_float(row.get("緯度"))

    if external_id is None or lon is None or lat is None:
        return None

    # 座標合理性檢查。大臺北地區大約在經度 121.3~121.8、緯度 24.8~25.4。
    # 常見的髒資料：0、空值、或經緯度寫反（121 跟 25 對調）。
    # 不檢查的話，地圖上會出現漂到非洲外海的點。
    if not (121.3 < lon < 121.8 and 24.8 < lat < 25.4):
        return None

    return {
        "external_id": external_id,
        # 場所名稱偶爾是空的，退而用設置地點，最後才用編號。
        # 不做這層 fallback，前端列表會出現一堆空白項目。
        "name": _clean(row.get("場所名稱"))
        or _clean(row.get("設置地點"))
        or external_id,
        "address": _clean(row.get("地址")),
        "city": _resolve_city(row),
        "district": _normalize_district(row.get("行政區")),
        "place_type": _clean(row.get("場所別")),
        "owner_unit": _clean(row.get("所屬單位")),
        "install_spot": _clean(row.get("設置地點")),
        "open_hours": _clean(row.get("場所開放時間")),
        "lon": lon,
        "lat": lat,
        "maintainer": _clean(row.get("維護單位")),
        "phone": _clean(row.get("連絡電話")),
        "status": _clean(row.get("狀態")),
        "status_changed_at": _to_datetime(row.get("狀態異動日期時間")),
        "last_sampled_at": _to_datetime(row.get("最近採樣日期時間")),
        "coliform": _clean(row.get("大腸桿菌數")),
        "quality_url": _clean(row.get("水質及維護資訊網址")),
        # 注意：來源欄位名用的是「直飲台」（台），不是「直飲臺」（臺）。
        # 同一份資料裡兩種寫法並存，打錯一個字就永遠拿不到照片。
        # 這就是為什麼一定要先看過真實資料再寫程式。
        "photo_url": _clean(row.get("直飲台照片網址")),
    }


def main() -> None:
    """
    只抓取與檢查，不寫入資料庫。
    執行：python -m app.opendata
    """
    print("抓取 data.taipei 開放資料…")
    rows = fetch_rows()

    valid: list[dict[str, Any]] = []
    skipped = 0
    for row in rows:
        mapped = to_station_dict(row)
        if mapped is None:
            skipped += 1
        else:
            valid.append(mapped)

    print()
    print(f"原始筆數 : {len(rows)}")
    print(f"可用筆數 : {len(valid)}")
    print(f"跳過筆數 : {skipped}（缺編號、缺座標、或座標超出合理範圍）")

    # 看一下「市別」的分布 —— 驗證我在 models.py 註解裡說的
    # 「這份資料含新北市的點」是不是真的
    from collections import Counter

    print()
    print("市別分布 :", dict(Counter(s["city"] for s in valid)))
    print("行政區數 :", len({s["district"] for s in valid}))

    print()
    print("第一筆對應結果：")
    for key, value in valid[0].items():
        print(f"  {key:20} = {value}")


if __name__ == "__main__":
    main()
