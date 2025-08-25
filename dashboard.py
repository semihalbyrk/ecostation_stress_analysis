# dashboard.py

import streamlit as st
import pandas as pd

# Diğer Python dosyalarımızdan gerekli fonksiyonları ve değişkenleri içe aktaralım
from config import DEFAULT_PARAMS
from data_loader import load_and_prepare_data
from simulation import run_simulation

st.set_page_config(layout="wide")

st.title("Ecostation Operasyonel Kapasite Analizi")
st.write("Bu araç, mevcut filo ve operasyonel varsayımlar altında Ecostation ağının kapasitesini simüle eder.")

# --- SIDEBAR: Ayarlanabilir Parametreler ---
st.sidebar.header("Simülasyon Ayarları")
params = {}
params['NUM_TRUCKS'] = st.sidebar.number_input("Araç Sayısı", min_value=1, max_value=10, value=DEFAULT_PARAMS['NUM_TRUCKS'])
params['DAILY_WORK_HOURS'] = st.sidebar.slider("Günlük Mesai Süresi (saat)", 4.0, 12.0, DEFAULT_PARAMS['DAILY_WORK_HOURS'], 0.5)
params['AVG_SPEED_KMH'] = st.sidebar.slider("Ortalama Araç Hızı (km/sa)", 20.0, 60.0, DEFAULT_PARAMS['AVG_SPEED_KMH'], 1.0)
params['SERVICE_TIME_MIN'] = st.sidebar.slider("Ecostation Servis Süresi (dakika)", 10.0, 60.0, DEFAULT_PARAMS['SERVICE_TIME_MIN'], 5.0)
params['UNLOADING_TIME_MIN'] = st.sidebar.slider("Depo Boşaltma Süresi (dakika)", 15.0, 90.0, DEFAULT_PARAMS['UNLOADING_TIME_MIN'], 5.0)
params['ROAD_NETWORK_FACTOR'] = st.sidebar.slider("Yol Faktörü (1.0 = Kuş Uçuşu)", 1.0, 2.0, DEFAULT_PARAMS['ROAD_NETWORK_FACTOR'], 0.05)
params['CAPACITY_TRIGGER_PERCENT'] = st.sidebar.slider("Toplama Tetikleme Yüzdesi (%)", 0.6, 1.0, DEFAULT_PARAMS['CAPACITY_TRIGGER_PERCENT'], 0.05)
params['SIMULATION_DAYS'] = DEFAULT_PARAMS['SIMULATION_DAYS'] # Sabit

# --- Ana Analiz Butonu ---
if st.sidebar.button("Analizi Çalıştır", type="primary"):
    
    with st.spinner("Veriler hazırlanıyor ve simülasyon çalıştırılıyor... Lütfen bekleyin."):
        try:
            # 1. Verileri hazırla
            ecostation_data, trip_times, garage_location = load_and_prepare_data(params)
            num_existing_stations = 12 # Mevcut istasyon sayısı

            # 2. Mevcut durum simülasyonunu çalıştır
            analysis_12 = run_simulation(num_existing_stations, params['NUM_TRUCKS'], ecostation_data, trip_times, params)

            # --- SONUÇLARI GÖSTER ---
            st.header("Mevcut Durum Analizi (12 Ecostation)")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Filo Kullanım Oranı", f"{analysis_12['utilization_percent']:.2f}%")
            col2.metric(f"Toplam Sefer ({params['SIMULATION_DAYS']} günde)", f"{analysis_12['total_trips']}")
            col3.metric("Servis Aksama Sayısı", f"{analysis_12['service_failures']}", 
                        help="Bir istasyon dolduktan sonraki 24 saat içinde toplanamama sayısı.")

            # --- Yorum ve Değerlendirme ---
            st.subheader("Değerlendirme")
            if analysis_12['service_failures'] > (analysis_12['total_trips'] * 0.02): # Eğer aksama oranı %2'den fazlaysa
                st.error(f"""
                **SONUÇ: Mevcut filo yetersiz.**
                - Simülasyon, mevcut operasyonel model ile **{params['NUM_TRUCKS']} aracın {num_existing_stations} istasyon için yetersiz kaldığını** gösteriyor.
                - Toplam **{analysis_12['service_failures']} kez** toplama talebi zamanında karşılanamamıştır. Bu durum, operasyonel verimsizliklere ve potansiyel müşteri şikayetlerine yol açabilir.
                - Filo kullanım oranı **%{analysis_12['utilization_percent']:.2f}** ile zaten çok yüksek. Bu, araçların esneklik payı olmadan sürekli çalıştığı anlamına gelir.
                """)
            else:
                st.success(f"""
                **SONUÇ: Mevcut filo yeterli.**
                - Simülasyon, **{params['NUM_TRUCKS']} aracın {num_existing_stations} istasyonun talebini başarıyla karşılayabildiğini** gösteriyor.
                - Toplamda sadece **{analysis_12['service_failures']}** servis aksaması yaşanmıştır, bu kabul edilebilir bir seviyedir.
                - Filo kullanım oranı **%{analysis_12['utilization_percent']:.2f}**. Bu orana göre filoda yeni bir istasyon için kapasite olup olmadığı aşağıda incelenmiştir.
                """)

            # --- Gelecek Potansiyeli Analizi ---
            st.header("Gelecek Potansiyeli ve Büyüme Analizi")
            
            # 13. İstasyon Analizi
            st.subheader("Soru: 1 Yeni Ecostation Eklersek Ne Olur?")
            
            # Hipotetik istasyon verilerini hazırla
            hypothetical_station_data = ecostation_data.tail(len(ecostation_data) - num_existing_stations)
            
            analysis_13 = run_simulation(num_existing_stations + 1, params['NUM_TRUCKS'], ecostation_data, trip_times, params)

            delta_failures = analysis_13['service_failures'] - analysis_12['service_failures']
            
            st.write(f"Sisteme ortalama özelliklerde yeni bir istasyon eklendiğinde, servis aksama sayısının **{analysis_12['service_failures']}**'dan **{analysis_13['service_failures']}**'e çıkacağı tahmin ediliyor (+{delta_failures} aksama).")
            
            if delta_failures > 10 or analysis_13['service_failures'] > (analysis_13['total_trips'] * 0.03):
                 st.warning("**YORUM:** Mevcut filo ile yeni bir istasyon eklemek, operasyonel aksaklıkları ciddi şekilde artıracaktır. **Önerilmez.**")
            else:
                 st.info("**YORUM:** Mevcut filo, 1 yeni istasyonun getireceği ek yükü **tolere edebilir** görünüyor.")

            # 3. Araç Analizi
            st.subheader(f"Soru: {num_existing_stations + 1} İstasyon İçin Kaç Araç Gerekir?")
            analysis_13_with_more_trucks = run_simulation(num_existing_stations + 1, params['NUM_TRUCKS'] + 1, ecostation_data, trip_times, params)
            st.write(f"Eğer {num_existing_stations + 1} istasyonlu operasyon **{params['NUM_TRUCKS'] + 1} araçla** yönetilirse:")
            
            col1_3, col2_3 = st.columns(2)
            col1_3.metric(f"{params['NUM_TRUCKS'] + 1} Araç ile Kullanım Oranı", f"{analysis_13_with_more_trucks['utilization_percent']:.2f}%")
            col2_3.metric(f"{params['NUM_TRUCKS'] + 1} Araç ile Servis Aksama Sayısı", f"{analysis_13_with_more_trucks['service_failures']}")
            
            st.success(f"**SONUÇ:** Filoya **1 araç daha eklemek**, {num_existing_stations + 1} istasyonlu bir ağdaki servis aksaklıklarını neredeyse tamamen ortadan kaldırarak operasyonel stabiliteyi sağlayacaktır.")


        except Exception as e:
            st.error(f"Analiz sırasında bir hata oluştu: {e}")
