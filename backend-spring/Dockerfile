# Spring Boot 版後端容器：兩階段建置（multi-stage build）
#
# 階段 1 用 JDK + Maven 把程式編譯成一個 jar 檔
# 階段 2 只把 jar 複製到 JRE 映像，JDK、Maven、原始碼全部丟掉
# 跟前端 Dockerfile 的思路一樣：跑起來不需要的東西，不要留在最終映像裡。

# ── 階段 1：編譯 ──────────────────────────────────────
FROM eclipse-temurin:25-jdk AS build
WORKDIR /app

# ⚠ 先只複製 Maven 設定，下載完依賴再複製原始碼。
# 只要 pom.xml 沒變，重新 build 時「下載依賴」這一層就直接用快取 ——
# 跟 backend/Dockerfile 先複製 requirements.txt 是同一個技巧。
COPY mvnw pom.xml ./
COPY .mvn .mvn
RUN chmod +x mvnw && ./mvnw -B -q dependency:go-offline

COPY src src
RUN ./mvnw -B -q package -DskipTests

# ── 階段 2：只留下 jar ────────────────────────────────
# JRE 只能「執行」Java，不能編譯，比 JDK 小很多
FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar

EXPOSE 8081
ENTRYPOINT ["java", "-jar", "app.jar"]
