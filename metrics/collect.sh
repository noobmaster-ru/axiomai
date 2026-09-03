#!/bin/sh
# Сборщик метрик хоста и контейнеров: раз в METRICS_INTERVAL секунд пишет JSON-строки
# в stdout, откуда их забирает Vector и складывает в Loki (см. docker-compose.grafana.yaml).
# /proc в контейнере отражает ХОСТ (meminfo/stat глобальные), диск хоста смонтирован в /host.

INTERVAL="${METRICS_INTERVAL:-30}"

while true; do
  # CPU хоста: два замера /proc/stat с паузой 3с
  c1=$(head -1 /proc/stat)
  sleep 3
  c2=$(head -1 /proc/stat)
  cpu_pct=$(printf '%s\n%s\n' "$c1" "$c2" | awk '
    NR==1 { for (i=2; i<=NF; i++) t1+=$i; i1=$5 }
    NR==2 { for (i=2; i<=NF; i++) t2+=$i; i2=$5 }
    END { dt=t2-t1; if (dt<=0) print 0; else printf "%.1f", 100*(dt-(i2-i1))/dt }')

  # Память и swap хоста
  mem_json=$(awk '
    /^MemTotal:/      { total=$2 }
    /^MemAvailable:/  { avail=$2 }
    /^SwapTotal:/     { st=$2 }
    /^SwapFree:/      { sf=$2 }
    END {
      used=total-avail
      printf "\"mem_used_mb\":%.0f,\"mem_total_mb\":%.0f,\"mem_used_pct\":%.1f,\"swap_used_mb\":%.0f",
        used/1024, total/1024, (total>0 ? 100*used/total : 0), (st-sf)/1024
    }' /proc/meminfo)

  # Диск хоста (корень смонтирован в /host)
  disk_json=$(df -Pk /host | awk 'NR==2 {
    printf "\"disk_used_pct\":%.1f,\"disk_used_gb\":%.1f,\"disk_total_gb\":%.1f",
      100*$3/($3+$4), $3/1048576, ($3+$4)/1048576 }')

  echo "{\"metric\":\"host\",\"cpu_pct\":$cpu_pct,$mem_json,$disk_json,\"level\":\"INFO\"}"

  # Метрики контейнеров: CPU% и память из docker stats
  docker stats --no-stream --format '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}' 2>/dev/null | awk -F'|' '
    function to_mb(s) {
      gsub(/ .*/, "", s)
      if (s ~ /GiB/) { gsub(/GiB/, "", s); return s*1024 }
      if (s ~ /MiB/) { gsub(/MiB/, "", s); return s+0 }
      if (s ~ /KiB/) { gsub(/KiB/, "", s); return s/1024 }
      gsub(/B/, "", s); return s/1048576
    }
    {
      cpu=$2; gsub(/%/, "", cpu)
      printf "{\"metric\":\"container\",\"svc\":\"%s\",\"cpu_pct\":%s,\"mem_mb\":%.1f,\"level\":\"INFO\"}\n",
        $1, (cpu==""?0:cpu), to_mb($3)
    }'

  sleep "$INTERVAL"
done
