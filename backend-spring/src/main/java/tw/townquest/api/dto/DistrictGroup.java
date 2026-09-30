package tw.townquest.api.dto;

import java.util.List;

/** 行政區清單，依縣市分組，前端可以直接塞進 &lt;optgroup&gt;。 */
public record DistrictGroup(String city, List<String> districts) {
}
