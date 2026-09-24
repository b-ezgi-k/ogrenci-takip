import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import plotly.express as px
import pandas as pd
import requests
from io import BytesIO
import urllib.parse

st.set_page_config(
    page_title="Öğrenci Takip Sistemi",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Renk ve tasarım kodları
tasarim_kodlari = """
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #FFFFFF;
    }
    
    /* Sekme Tasarımları */
    button[data-baseweb="tab"] {
        color: #31333F !important;
        border-bottom-color: #FF4B4B !important;
    }
    
    div[data-baseweb="tab-highlight-bar"] {
        background-color: #FF4B4B !important;
    }
    
    /* Buton Tasarımı */
    .stButton>button {
        color: #FF4B4B !important;
        border-color: #FF4B4B !important;
        background-color: transparent !important;
        border-radius: 12px !important;
    }
    
    .stButton>button:hover {
        background-color: #FF4B4B !important;
        color: #FFFFFF !important;
    }
    
    /* Yan Menü Arka Planı */
    [data-testid="stSidebar"] {
        background-color: #F0F2F6;
    }
    
    html {
        --primary: #FF4B4B !important;
    }
</style>
"""

st.markdown(tasarim_kodlari, unsafe_allow_html=True)

# PDF Üretimi İçin ReportLab Kitaplıkları
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Supabase Bağlantı Bilgileri
SUPABASE_URL = "https://aasptqqypnshuanmwbko.supabase.co"
SUPABASE_KEY = "sb_publishable_ILbUCJ_olLbcV13gabNOdQ_1g66fh2U"

# 🔑 Öğretmen Şifresi
OGRETMEN_ANA_SIFRESI = "MathPie2026"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

def dosya_adi_temizle(metin):
    turkce_karakterler = {"ç": "c", "ğ": "g", "ı": "i", "i": "i", "ö": "o", "ş": "s", "ü": "u", "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U"}
    for kaynak, hedef in turkce_karakterler.items():
        metin = metin.replace(kaynak, hedef)
    metin = metin.replace(" ", "-")
    return metin.lower()

def pdf_olustur(ogrenci_adi, konu_adi, gorsel_listesi):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'BaslikStil',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=15
    )
    
    question_style = ParagraphStyle(
        'SoruStil',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=5
    )
    
    baslik_metni = f"{ogrenci_adi} - {konu_adi} Ozel Tarama Fasikulu"
    story.append(Paragraph(baslik_metni, title_style))
    story.append(Spacer(1, 10))
    
    for oge in gorsel_listesi:
        story.append(Paragraph(f"• {oge['tanim']}", question_style))
        
        try:
            response = requests.get(oge['url'], timeout=10)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                img = Image(img_data)
                
                orijinal_genislik = img.drawWidth
                orijinal_yukseklik = img.drawHeight
                
                MAKS_GENISLIK = 450
                MAKS_YUKSEKLIK = 500  
                
                yeni_genislik = MAKS_GENISLIK
                yeni_yukseklik = (orijinal_yukseklik * MAKS_GENISLIK) / orijinal_genislik
                
                if yeni_yukseklik > MAKS_YUKSEKLIK:
                    yeni_yukseklik = MAKS_YUKSEKLIK
                    yeni_genislik = (orijinal_genislik * MAKS_YUKSEKLIK) / orijinal_yukseklik
                
                img.drawWidth = yeni_genislik
                img.drawHeight = yeni_yukseklik
                story.append(img)
            else:
                story.append(Paragraph("[Gorsel Yuklenemedi]", styles['Normal']))
        except Exception as e:
            story.append(Paragraph(f"[Gorsel Hatasi: {str(e)}]", styles['Normal']))
            
        story.append(Spacer(1, 15))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# Sayfa Modu Seçimi
st.sidebar.title("📱 Panel Seçimi")
panel_modu = st.sidebar.radio("Sisteme Kim Olarak Giriş Yapıyorsunuz?", ["Öğretmen Paneli", "Öğrenci Girişi"])

@st.cache_data(ttl=30)
def kitaplari_getir():
    try:
        res = supabase.table("books").select("id, book_name").execute()
        return res.data if res else []
    except Exception:
        st.sidebar.error("⚠️ Veritabanı bağlantısı kurulamadı.")
        return []

@st.cache_data(ttl=30)
def ogrencileri_getir():
    try:
        res = supabase.table("student_list").select("*").execute()
        return res.data if res else []
    except Exception:
        return []

kitaplar_listesi = kitaplari_getir()
kitap_id_to_name = {k["id"]: k["book_name"] for k in kitaplar_listesi} if kitaplar_listesi else {}

ogrenciler_data_list = ogrencileri_getir()
tum_ogrenciler = [o["student_name"] for o in ogrenciler_data_list] if ogrenciler_data_list else []

# ==========================================
# ÖĞRETMEN PANELİ
# ==========================================
if panel_modu == "Öğretmen Paneli":
    st.title("📊 Öğretmen Yönetim ve Analiz Raporu")
    st.write("---")
    
    st.subheader("🔒 Yönetici Girişi")
    hocam_sifre = st.text_input("Lütfen Öğretmen Giriş Şifrenizi Girin:", type="password", key="hoca_sifre_kutusu")
    
    if hocam_sifre == OGRETMEN_ANA_SIFRESI:
        st.success("🔑 Giriş Başarılı. Hoş geldiniz hocam!")
        st.write("---")
        
        sekme1, sekme2, sekme3, sekme4, sekme5 = st.tabs([
            "📥 Gelen Bildirimler", 
            "📚 KONU BAZLI HATA KİTAPÇIĞI",
            "📅 Günlük Ödev Takip", 
            "📈 Gelişim Grafikleri",
            "👥 Sınıf ve Müfredat Yönetimi"
        ])
        
        with sekme1:
            st.header("🔍 İncelenmemiş Öğrenci Hataları")
            try:
                yeni_sonuclar = supabase.table("student_results").select("*").eq("is_checked", False).order("created_at", desc=True).execute()
                gelen_veri = yeni_sonuclar.data if yeni_sonuclar else []
            except Exception as err:
                st.error(f"Veri çekilirken bir hata oluştu: {err}")
                gelen_veri = []
            
            if gelen_veri:
                for rapor in gelen_veri:
                    raw_w = rapor.get("wrong_questions", "")
                    tur_ve_no = "Bilinmeyen Soru"
                    if "::" in raw_w:
                        tur_ve_no = raw_w.split("::")[0]
                    
                    r_sol, r_sag = st.columns([4, 1])
                    with r_sol:
                        st.write(f"👤 **Öğrenci:** {rapor['student_name']} | 📌 **{tur_ve_no}** | 📅 **Tarih:** {rapor.get('created_at', '')[:10]}")
                    with r_sag:
                        if st.button("✓ Kontrol Edildi", key=f"check_{rapor['id']}"):
                            supabase.table("student_results").update({"is_checked": True}).eq("id", rapor["id"]).execute()
                            st.success("Test arşivlendi!")
                            st.cache_data.clear()
                            st.rerun()
                    st.write("---")
            else:
                st.success("🎉 Harika! İncelenmemiş hiç ödev/hata bildirimi kalmadı.")

        with sekme2:
            st.header("📚 Konu Bazlı Tarama Kitapçığı")
            st.write("Öğrencinin geçmişte yüklediği tüm yanlış ve boş soruları filtreleyip PDF dosyası olarak indirebilirsiniz.")
            
            if tum_ogrenciler:
                c_k1, c_k2, c_k3 = st.columns(3)
                with c_k1: t_ogrenci = st.selectbox("1. Öğrenci Seçin:", tum_ogrenciler, key="tarama_o")
                with c_k2: t_kitap = st.selectbox("2. Kitap Seçin:", list(kitap_id_to_name.values()) if kitap_id_to_name else ["Kitap Yok"], key="tarama_k")
                
                selected_book_id = None
                if kitap_id_to_name and t_kitap in kitap_id_to_name.values():
                    selected_book_id = [k for k, v in kitap_id_to_name.items() if v == t_kitap][0]

                konu_haritasi_tarama = {}
                if selected_book_id:
                    konular_db = supabase.table("subjects").select("id", "subject_name").eq("book_id", selected_book_id).execute()
                    if konular_db and konular_db.data:
                        konu_haritasi_tarama = {kon["subject_name"]: kon["id"] for kon in konular_db.data}

                with c_k3: 
                    t_konu = st.selectbox("3. Konu Seçin:", list(konu_haritasi_tarama.keys()) if konu_haritasi_tarama else ["Konu Bulunamadı"], key="tarama_konu")
                
                if selected_book_id and t_konu != "Konu Bulunamadı":
                    if st.button("🔍 Tarama Verilerini Topla"):
                        secilen_konu_id = konu_haritasi_tarama[t_konu]
                        testler_db = supabase.table("tests").select("id").eq("subject_id", secilen_konu_id).execute()
                        test_idleri = [t["id"] for t in testler_db.data] if (testler_db and testler_db.data) else []
                        
                        if test_idleri:
                            ogrenci_raporlari = supabase.table("student_results").select("*").eq("student_name", t_ogrenci).in_("test_id", test_idleri).execute()
                            
                            gorsel_listesi = []
                            if ogrenci_raporlari and ogrenci_raporlari.data:
                                for rapor in ogrenci_raporlari.data:
                                    wrong_urls_str = rapor.get("wrong_questions", "")
                                    if "http" in wrong_urls_str:
                                        linkler = wrong_urls_str.split("|||")
                                        for link_detay in linkler:
                                            if "::" in link_detay:
                                                tur_ve_no, url = link_detay.split("::")
                                                gorsel_listesi.append({"tanim": tur_ve_no, "url": url})
                            
                            if len(gorsel_listesi) > 0:
                                st.success(f"🎉 Toplam {len(gorsel_listesi)} adet hatalı/boş soru görseli başarıyla toplandı!")
                                
                                temiz_dosya_adi = dosya_adi_temizle(f"{t_ogrenci}-{t_konu}-tarama.pdf")
                                pdf_data = pdf_olustur(t_ogrenci, t_konu, gorsel_listesi)
                                
                                st.download_button(
                                    label="📥 FASİKÜLÜ PDF OLARAK BİLGİSAYARA İNDİR",
                                    data=pdf_data,
                                    file_name=temiz_dosya_adi,
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                                
                                st.write("---")
                                st.subheader("👀 Ekran Önizlemesi")
                                for g in gorsel_listesi:
                                    st.write(f"📌 **{g['tanim']}**")
                                    st.image(g['url'], width=400)
                            else:
                                st.warning("Bu konuda öğrenciye ait yüklenmiş herhangi bir soru görseli bulunamadı.")
                        else: 
                            st.warning("Bu konuya ait henüz sistemde tanımlı bir test bulunmuyor.")

        with sekme3:
            st.header("📅 Günlük Ödev Durum Tablosu")
            secilen_tarih = st.date_input("Hangi Günün Ödev Kontrolünü Görmek İstersiniz?", datetime.today())
            tarih_str = secilen_tarih.strftime("%Y-%m-%d")
            
            if len(tum_ogrenciler) == 0:
                st.warning("Öğrencilerinizi eklemek için 'Sınıf ve Müfredat Yönetimi' sekmesini kullanın.")
            else:
                st.write("---")
                st.subheader("✉️ Günlük WhatsApp Hatırlatma Mesajı Taslağı")
                varsayilan_mesaj = "Math Pie sisteminde bugün yapman gereken ödev/hata girişi eksik görünmektedir. Sürecinin aksamaması için gün bitmeden eksiklerini tamamlamanı bekliyorum. İyi çalışmalar! 🥧"
                
                taslak_mesaj = st.text_area("Mesajınızı özelleştirebilirsiniz:", value=varsayilan_mesaj, height=100, key="dinamik_taslak_input")
                st.write("---")

                bugun_gonderenler_data = supabase.table("student_results").select("student_name").gte("created_at", f"{tarih_str}T00:00:00").lte("created_at", f"{tarih_str}T23:59:59").execute()
                yapanlar = list(set([b["student_name"] for b in bugun_gonderenler_data.data])) if (bugun_gonderenler_data and bugun_gonderenler_data.data) else []
                
                g_sol, g_sag = st.columns(2)
                with g_sol:
                    st.subheader(f"🟢 Ödevini Yapanlar ({len(yapanlar)})")
                    for y_ogrenci in yapanlar: 
                        st.write(f"✅ {y_ogrenci}")
                        
                with g_sag:
                    st.subheader(f"🔴 Ödevini Yapmayanlar")
                    ogrenci_telefon_haritasi = {o["student_name"]: o.get("student_phone", "") for o in ogrenciler_data_list} if ogrenciler_data_list else {}
                    
                    yapmayan_sayisi = 0
                    for yap_ogrenci in tum_ogrenciler:
                        if yap_ogrenci not in yapanlar:
                            yapmayan_sayisi += 1
                            col_isim, col_buton = st.columns([2, 1])
                            
                            with col_isim:
                                st.write(f"❌ {yap_ogrenci}")
                                
                            with col_buton:
                                tam_mesaj = f"Merhaba {yap_ogrenci},\n\n{taslak_mesaj}"
                                kodlanmis_mesaj = urllib.parse.quote(tam_mesaj)
                                ham_tel = str(ogrenci_telefon_haritasi.get(yap_ogrenci, "")).strip()
                                
                                if ham_tel == "" or ham_tel == "None":
                                    whatsapp_linki = f"https://wa.me/?text={kodlanmis_mesaj}"
                                else:
                                    if ham_tel.startswith("0"):
                                        ham_tel = "90" + ham_tel[1:]
                                    elif not ham_tel.startswith("90"):
                                        ham_tel = "90" + ham_tel
                                    whatsapp_linki = f"https://wa.me/{ham_tel}?text={kodlanmis_mesaj}"
                                
                                st.markdown(f'[@button Hatırlat 💬]({whatsapp_linki})', unsafe_allow_html=True)
                    
                    if yapmayan_sayisi == 0:
                        st.success("Harika! Bugün tüm sınıf ödev girişlerini tamamladı. 🎉")

        with sekme4:
            st.header("📈 Akıllı Grafik Analizleri")
            st.info("Sistemdeki öğrenci çözümleri burada görsel grafiklere dönüştürülür.")

        # SEKME 5: SINIF VE MÜFREDAT YÖNETİMİ
        with sekme5:
            st.header("👥 Sınıf Listesi ve Kitap Atama")
            
            # ➕ YENİ ÖĞRENCİ EKLEME ALANI
            st.subheader("➕ Yeni Öğrenci Ekle")
            c_ekle1, c_ekle2, c_ekle3 = st.columns(3)
            with c_ekle1: y_ad = st.text_input("Ad Soyad:")
            with c_ekle2: y_num = st.text_input("Okul / Giriş Numarası:")
            with c_ekle3: y_sifre = st.text_input("Giriş Şifresi:", type="password")
                
            if st.button("Öğrenciyi Kaydet"):
                if y_ad and y_num and y_sifre:
                    supabase.table("student_list").insert({
                        "student_name": y_ad, 
                        "student_number": y_num, 
                        "student_password": y_sifre
                    }).execute()
                    st.success(f"'{y_ad}' başarıyla eklendi!")
                    st.cache_data.clear()
                    st.rerun()
            
            # 📋 KAYITLI ÖĞRENCİ LİSTESİ VE SİLME ALANI
            st.write("---")
            st.subheader("📋 Kayıtlı Öğrenci Listesi")
            if ogrenciler_data_list:
                for ogr in ogrenciler_data_list:
                    col_info, col_del = st.columns([4, 1])
                    with col_info:
                        st.write(f"👤 **{ogr['student_name']}** | No: `{ogr.get('student_number', '-')}` | Şifre: `{ogr.get('student_password', '-')}`")
                    with col_del:
                        if st.button("Sil 🗑️", key=f"del_ogr_{ogr['id']}"):
                            supabase.table("student_list").delete().eq("id", ogr["id"]).execute()
                            st.success(f"{ogr['student_name']} silindi.")
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("Sistemde henüz kayıtlı öğrenci bulunmuyor.")

            # 🎯 KİTAP ATAMA VE ATANAN KİTAPLARI GÖRÜNTÜLEME/SİLME ALANI
            st.write("---")
            st.subheader("🎯 Öğrenciye Özel Kitap Atama Paneli")
            if tum_ogrenciler and kitaplar_listesi:
                c1, c2 = st.columns(2)
                with c1: secilen_atama_ogrencisi = st.selectbox("Öğrenci Seçin:", tum_ogrenciler, key="atama_o")
                with c2: secilen_atama_kitabi = st.selectbox("Tanımlanacak Kitabı Seçin:", list(kitap_id_to_name.values()), key="atama_k")
                
                if st.button("Kitabı Bu Öğrenciye Tanımla"):
                    try:
                        k_id = [k for k, v in kitap_id_to_name.items() if v == secilen_atama_kitabi][0]
                        supabase.table("student_book_assignments").insert({
                            "student_name": secilen_atama_ogrencisi, 
                            "book_id": k_id
                        }).execute()
                        st.success(f"'{secilen_atama_kitabi}' başarıyla {secilen_atama_ogrencisi} kullanıcısına atandı!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as err:
                        st.error(f"⚠️ Kitap atanırken hata oluştu (Sütun adlarını veya Supabase tablosunu kontrol edin): {err}")

            # 📖 HANGİ ÖĞRENCİNİN HANGİ KİTAPLARI KULLANDIĞINI GÖSTEREN TABLO
            st.write("---")
            st.subheader("📚 Öğrencilere Tanımlı Kitap Listesi")
            try:
                atama_veri = supabase.table("student_book_assignments").select("*").execute()
                atama_listesi = atama_veri.data if atama_veri else []
                
                if atama_listesi:
                    for atama in atama_listesi:
                        ogrenci_isimi = atama.get("student_name", "Bilinmeyen Öğrenci")
                        kitap_numarasi = atama.get("book_id")
                        kitap_isimi = kitap_id_to_name.get(kitap_numarasi, f"Kitap ID: {kitap_numarasi}")
                        
                        col_atama_info, col_atama_del = st.columns([4, 1])
                        with col_atama_info:
                            st.write(f"👤 **{ogrenci_isimi}** ➔ 📖 **{kitap_isimi}**")
                        with col_atama_del:
                            if st.button("Atamayı Kaldır 🗑️", key=f"del_atama_{atama['id']}"):
                                supabase.table("student_book_assignments").delete().eq("id", atama["id"]).execute()
                                st.success("Kitap ataması kaldırıldı.")
                                st.cache_data.clear()
                                st.rerun()
                else:
                    st.info("Henüz hiçbir öğrenciye kitap tanımlanmamış.")
            except Exception as e:
                st.warning(f"Kitap atama verileri çekilemedi: {e}")

            st.write("---")
            st.header("📚 Mevcut Müfredat Yapısı ve Veri Ekleme/Silme")
            if kitaplar_listesi:
                for kitap in kitaplar_listesi:
                    ks_l, ks_r = st.columns([5, 1])
                    with ks_l: st.subheader(f"📖 {kitap['book_name']}")
                    with ks_r:
                        if st.button("Kitabı Sil 🗑️", key=f"sil_k_{kitap['id']}"):
                            supabase.table("books").delete().eq("id", kitap["id"]).execute()
                            st.cache_data.clear()
                            st.rerun()
                            
                    konular_data = supabase.table("subjects").select("id", "subject_name").eq("book_id", kitap["id"]).execute()
                    if konular_data and konular_data.data:
                        for konu in konular_data.data:
                            kons_l, kons_r = st.columns([5, 1])
                            with kons_l: st.markdown(f"**&nbsp;&nbsp;&nbsp;&nbsp;🔸 {konu['subject_name']}**")
                            with kons_r:
                                if st.button("Konuyu Sil 🗑️", key=f"sil_kon_{konu['id']}"):
                                    supabase.table("subjects").delete().eq("id", konu["id"]).execute()
                                    st.cache_data.clear()
                                    st.rerun()
            
            st.write("---")
            st.subheader("➕ 1. Yeni Kitap Ekle")
            y_kitap = st.text_input("Kitap Adı Yazın (Örn: 345 Matematik):", key="ekle_k_input")
            if st.button("Kitabı Kaydet"):
                if y_kitap: 
                    supabase.table("books").insert({"book_name": y_kitap}).execute()
                    st.cache_data.clear()
                    st.rerun()
            
            if kitaplar_listesi:
                st.write("---")
                st.subheader("➕ 2. Yeni Konu Ekle")
                k_secim_listesi = {k["book_name"]: k["id"] for k in kitaplar_listesi}
                secilen_konu_kitabi = st.selectbox("Hangi Kitaba Konu Eklemek İstersiniz?", list(k_secim_listesi.keys()), key="konu_k_sec")
                y_konu = st.text_input("Konu Adı Yazın (Örn: Fonksiyonlar):", key="ekle_konu_input")
                if st.button("Konuyu Kaydet"):
                    if y_konu: 
                        y_konu_res = supabase.table("subjects").insert({"subject_name": y_konu, "book_id": k_secim_listesi[secilen_konu_kitabi]}).execute()
                        if y_konu_res and y_konu_res.data:
                            yeni_konu_id = y_konu_res.data[0]["id"]
                            supabase.table("tests").insert({"test_name": f"{y_konu} - 100 Soru Havuzu", "total_questions": 100, "subject_id": yeni_konu_id}).execute()
                        st.cache_data.clear()
                        st.success(f"'{y_konu}' konusu ve 100 soruluk fotoğraf alanı otomatik oluşturuldu!")
                        st.rerun()

    elif hocam_sifre != "": 
        st.error("❌ Hatalı Yönetici Şifresi!")

# ==========================================
# ÖĞRENCİ PANELİ (100 Soru Sıralı & Kilitli Sistem)
# ==========================================
else:
    st.title("🎯 Öğrenci Soru/Hata Bildirim Ekranı")
    st.write("---")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        g_numara = st.text_input("Öğrenci Numaranız:", key="ogr_no")
    with col_g2:
        g_sifre = st.text_input("Giriş Şifreniz:", type="password", key="ogr_pass")

    if g_numara and g_sifre:
        ogrenci_sorgu = supabase.table("student_list").select("*").eq("student_number", g_numara).eq("student_password", g_sifre).execute()
        
        if ogrenci_sorgu and ogrenci_sorgu.data:
            ogr_bilgi = ogrenci_sorgu.data[0]
            ogrenci_adi = ogr_bilgi["student_name"]
            st.success(f"👋 Hoş geldin, **{ogrenci_adi}**!")
            st.write("---")
            
            atama_sorgusu = supabase.table("student_book_assignments").select("book_id").eq("student_name", ogrenci_adi).execute()
            atanan_book_idleri = [a["book_id"] for a in atama_sorgusu.data] if (atama_sorgusu and atama_sorgusu.data) else []
            
            if atanan_book_idleri:
                atanan_kitaplar_data = supabase.table("books").select("id", "book_name").in_("id", atanan_book_idleri).execute()
                atanan_kitap_haritasi = {k["book_name"]: k["id"] for k in atanan_kitaplar_data.data} if (atanan_kitaplar_data and atanan_kitaplar_data.data) else {}
                
                secilen_o_kitap = st.selectbox("1. Kitap Seçin:", list(atanan_kitap_haritasi.keys()), key="o_k_sec")
                secilen_o_kitap_id = atanan_kitap_haritasi[secilen_o_kitap]
                
                konular_db = supabase.table("subjects").select("id", "subject_name").eq("book_id", secilen_o_kitap_id).execute()
                if konular_db and konular_db.data:
                    konu_haritasi = {kon["subject_name"]: kon["id"] for kon in konular_db.data}
                    secilen_o_konu = st.selectbox("2. Konu Seçin:", list(konu_haritasi.keys()), key="o_konu_sec")
                    secilen_o_konu_id = konu_haritasi[secilen_o_konu]
                    
                    testler_db = supabase.table("tests").select("id", "test_name", "total_questions").eq("subject_id", secilen_o_konu_id).execute()
                    
                    if testler_db and testler_db.data:
                        secilen_test_obj = testler_db.data[0]
                        test_id = secilen_test_obj["id"]
                        
                        mevcut_kayitlar = supabase.table("student_results").select("*").eq("student_name", ogrenci_adi).eq("test_id", test_id).execute()
                        
                        yuklenen_sorular = {}
                        if mevcut_kayitlar and mevcut_kayitlar.data:
                            for r in mevcut_kayitlar.data:
                                w_str = r.get("wrong_questions", "")
                                if "::" in w_str:
                                    s_no_metin, url = w_str.split("::")
                                    try:
                                        s_no = int(s_no_metin.replace("Soru", "").strip())
                                        yuklenen_sorular[s_no] = url
                                    except:
                                        pass

                        st.write("---")
                        st.subheader(f"📸 {secilen_o_konu} - 100 Soru Yükleme Paneli")
                        
                        siradaki_soru_no = 1
                        while siradaki_soru_no in yuklenen_sorular and siradaki_soru_no <= 100:
                            siradaki_soru_no += 1
                        
                        if siradaki_soru_no <= 100:
                            st.info(f"📌 **Sıradaki Yüklenecek Soru: Soru {siradaki_soru_no}** (Önceki sorular kilitlidir, değiştirilemez.)")
                            
                            uploaded_file = st.file_uploader(
                                f"Soru {siradaki_soru_no} Fotoğrafını Seçin (JPG, PNG):", 
                                type=["jpg", "jpeg", "png"],
                                key=f"uploader_s_{siradaki_soru_no}"
                            )
                            
                            if st.button(f"🚀 Soru {siradaki_soru_no}'i Kaydet ve İlerle", use_container_width=True):
                                if uploaded_file:
                                    with st.spinner("Fotoğraf güvenli bir şekilde yükleniyor..."):
                                        zaman_damgasi = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        dosya_uzantisi = uploaded_file.name.split(".")[-1]
                                        dosya_yolu = f"{dosya_adi_temizle(ogrenci_adi)}/{dosya_adi_temizle(secilen_o_konu)}/soru_{siradaki_soru_no}_{zaman_damgasi}.{dosya_uzantisi}"
                                        
                                        dosya_baytlari = uploaded_file.read()
                                        
                                        try:
                                            supabase.storage.from_("question_images").upload(
                                                path=dosya_yolu,
                                                file=dosya_baytlari,
                                                file_options={"content-type": uploaded_file.type}
                                            )
                                        except Exception as storage_err:
                                            st.error("⚠️ Fotoğraf Supabase depolama alanına yüklenemedi!")
                                            st.info("Lütfen Supabase panelinizde 'question_images' adında PUBLIC bir bucket oluşturulduğundan ve Policies kısmından INSERT izinlerinin açık olduğundan emin olun.")
                                            st.stop()
                                        
                                        public_url = supabase.storage.from_("question_images").get_public_url(dosya_yolu)
                                        formatli_veri = f"Soru {siradaki_soru_no}::{public_url}"
                                        
                                        supabase.table("student_results").insert({
                                            "student_name": ogrenci_adi,
                                            "test_id": test_id,
                                            "wrong_questions": formatli_veri,
                                            "blank_questions": "",
                                            "is_checked": False
                                        }).execute()
                                        
                                        st.success(f"✅ Soru {siradaki_soru_no} başarıyla kaydedildi ve kilitlendi!")
                                        st.rerun()
                                else:
                                    st.warning("Lütfen fotoğraf yükleyin.")
                                        
                                        st.success(f"✅ Soru {siradaki_soru_no} başarıyla kaydedildi ve kilitlendi!")
                                        st.rerun()
                                else:
                                    st.warning("Lütfen fotoğraf yükleyin.")
                        else:
                            st.balloons()
                            st.success("🎉 Tebrikler! Bu konudaki tüm 100 sorunun yüklemesini tamamladınız.")

                        st.write("---")
                        st.subheader("🔒 Yüklenen ve Kilitlenen Sorular")
                        
                        if yuklenen_sorular:
                            for s_num in sorted(yuklenen_sorular.keys()):
                                with st.expander(f"🔒 Soru {s_num} (Kilitli - Değiştirilemez)"):
                                    st.image(yuklenen_sorular[s_num], width=350)
                        else:
                            st.write("Henüz yüklenmiş soru bulunmamaktadır.")

                    else:
                        st.warning("Bu konuya tanımlı soru alanı bulunamadı.")
                else:
                    st.warning("Bu kitaba tanımlı konu bulunamadı.")
            else:
                st.warning("Henüz size tanımlanmış bir kitap bulunmuyor. Lütfen öğretmeninizle iletişime geçin.")
        else:
            st.error("❌ Okul numarası veya şifre hatalı!")
