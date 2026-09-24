import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import plotly.express as px
import pandas as pd
import requests
from io import BytesIO
import urllib.parse

# 1. SAYFA YAPILANDIRMASI VE TASARIM
st.set_page_config(
    page_title="Math Pie - Hata Takip Sistemi",
    layout="wide",
    initial_sidebar_state="expanded"
)

tasarim_kodlari = """
<style>
    .stApp { background-color: #FFFFFF; }
    button[data-baseweb="tab"] { color: #31333F !important; border-bottom-color: #FF4B4B !important; }
    div[data-baseweb="tab-highlight-bar"] { background-color: #FF4B4B !important; }
    .stButton>button { color: #FF4B4B !important; border-color: #FF4B4B !important; background-color: transparent !important; border-radius: 12px !important; }
    .stButton>button:hover { background-color: #FF4B4B !important; color: #FFFFFF !important; }
    [data-testid="stSidebar"] { background-color: #F0F2F6; }
    html { --primary: #FF4B4B !important; }
</style>
"""
st.markdown(tasarim_kodlari, unsafe_allow_html=True)

# 2. REPORTLAB PDF KÜTÜPHANELERİ
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 3. SUPABASE VE ANA ŞİFRE BAĞLANTILARI
SUPABASE_URL = "https://aasptqqypnshuanmwbko.supabase.co"
SUPABASE_KEY = "sb_publishable_ILbUCJ_olLbcV13gabNOdQ_1g66fh2U"
OGRETMEN_ANA_SIFRESI = "MathPie2026"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"⚠️ Supabase bağlantısı kurulamadı: {e}")
        return None

supabase = init_supabase()

# 4. YARDIMCI FONKSİYONLAR
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
        textColor=colors.HexColor("#FF4B4B"),
        alignment=1,
        spaceAfter=15
    )
    question_style = ParagraphStyle(
        'SoruStil',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=10,
        spaceAfter=5
    )
    
    story.append(Paragraph(f"<b>🥧 Math Pie - Özel Hata ve Boş Tarama Kitapçığı</b>", title_style))
    story.append(Paragraph(f"<b>Öğrenci:</b> {ogrenci_adi} | <b>Konu:</b> {konu_adi} | <b>Soru Sayısı:</b> {len(gorsel_listesi)}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    for idx, item in enumerate(gorsel_listesi, 1):
        story.append(Paragraph(f"Soru {idx} - ({item['durum']}):", question_style))
        try:
            response = requests.get(item['url'], timeout=5)
            if response.status_code == 200:
                img_data = BytesIO(response.content)
                img = RLImage(img_data)
                
                orijinal_g = img.drawWidth
                orijinal_y = img.drawHeight
                MAKS_G, MAKS_Y = 400, 450
                
                yeni_g = MAKS_G
                yeni_y = (orijinal_y * MAKS_G) / orijinal_g if orijinal_g > 0 else MAKS_Y
                if yeni_y > MAKS_Y:
                    yeni_y = MAKS_Y
                    yeni_g = (orijinal_g * MAKS_Y) / orijinal_y if orijinal_y > 0 else MAKS_G
                
                img.drawWidth = yeni_g
                img.drawHeight = yeni_y
                story.append(img)
            else:
                story.append(Paragraph("[Görsel Yüklenemedi]", styles['Normal']))
        except Exception as e:
            story.append(Paragraph(f"[Görsel Yükleme Hatası: {e}]", styles['Normal']))
        story.append(Spacer(1, 15))
        
    doc.build(story)
    buffer.seek(0)
    return buffer

# 5. PANEL SEÇİMİ (SIDEBAR)
st.sidebar.title("📱 Panel Seçimi")
panel_modu = st.sidebar.radio("Sisteme Kim Olarak Giriş Yapıyorsunuz?", ["Öğrenci Girişi", "Öğretmen Paneli"])

# Ortak Öğrenci Listesi Çekme
@st.cache_data(ttl=30)
def ogrencileri_getir():
    if not supabase: return []
    try:
        res = supabase.table("student_list").select("*").execute()
        return res.data if res.data else []
    except Exception:
        return []

ogrenciler_data = ogrencileri_getir()
tum_ogrenciler = [o["student_name"] for o in ogrenciler_data]

# ==========================================
# ÖĞRENCİ PANELİ (SADELEŞTİRİLMİŞ HATA TAKİP)
# ==========================================
if panel_modu == "Öğrenci Girişi":
    st.title("🎯 Öğrenci Soru/Hata Bildirim Ekranı")
    st.write("Yapamadığınız veya boş bıraktığınız soruların fotoğrafını çekip konu başlığıyla birlikte yükleyin.")
    st.write("---")
    
    if tum_ogrenciler:
        secilen_ogrenci = st.selectbox("Adınızı ve Soyadınızı Seçin:", tum_ogrenciler)
        g_sifre = st.text_input("Giriş Şifreniz:", type="password")
        
        # Öğrenci Şifre Doğrulama
        ogrenci_bilgi = next((o for o in ogrenciler_data if o["student_name"] == secilen_ogrenci), None)
        
        if g_sifre != "":
            if ogrenci_bilgi and str(ogrenci_bilgi.get("student_password", "")) == g_sifre:
                st.success(f"Hoş geldin {secilen_ogrenci}! Hatalı sorularını aşağıdan gönderebilirsin.")
                
                with st.form("hata_yukleme_formu", clear_on_submit=True):
                    konu_adi = st.text_input("Konu Adı (Örn: Üslü İfadeler, Trigonometri):")
                    durum = st.selectbox("Soru Durumu:", ["Yanlış Soru", "Boş Soru"])
                    yuklenen_dosya = st.file_uploader("Soru Fotoğrafı Seçin / Çekin:", type=["jpg", "jpeg", "png"])
                    
                    btn_gonder = st.form_submit_button("🚀 Soruyu Kaydet ve Gönder")
                    
                    if btn_gonder:
                        if konu_adi and yuklenen_dosya:
                            try:
                                # Storage'a Yükle
                                temiz_dosya = f"{dosya_adi_temizle(secilen_ogrenci)}_{dosya_adi_temizle(konu_adi)}_{yuklenen_dosya.name}"
                                bucket_name = "question_images"
                                
                                supabase.storage.from_(bucket_name).upload(temiz_dosya, yuklenen_dosya.read(), {"content-type": yuklenen_dosya.type})
                                gorsel_url = supabase.storage.from_(bucket_name).get_public_url(temiz_dosya)
                                
                                # Veritabanına Kaydet
                                supabase.table("student_errors").insert({
                                    "student_name": secilen_ogrenci,
                                    "topic_name": konu_adi,
                                    "error_type": durum,
                                    "image_url": gorsel_url,
                                    "is_checked": False
                                }).execute()
                                
                                st.balloons()
                                st.success("🎉 Sorun başarıyla öğretmenine iletildi!")
                            except Exception as e:
                                st.error(f"Soru yüklenirken bir hata oluştu: {e}")
                        else:
                            st.warning("Lütfen konu adını yazın ve fotoğraf yükleyin.")
            else:
                st.error("❌ Şifre hatalı! Lütfen tekrar deneyin.")
    else:
        st.info("Sistemde kayıtlı öğrenci bulunamadı. Lütfen öğretmeninizin sizi sisteme eklemesini bekleyin.")

# ==========================================
# ÖĞRETMEN PANELİ (ŞİFRE KORUMALI)
# ==========================================
else:
    st.title("📊 Öğretmen Yönetim ve Analiz Raporu")
    st.write("---")
    
    hocam_sifre = st.text_input("Lütfen Öğretmen Giriş Şifrenizi Girin:", type="password", key="hoca_sifre_kutusu")
    
    if hocam_sifre == OGRETMEN_ANA_SIFRESI:
        st.success("🔑 Giriş Başarılı. Hoş geldiniz hocam!")
        st.write("---")
        
        sekme1, sekme2, sekme3, sekme4 = st.tabs([
            "📥 Gelen Hata Bildirimleri", 
            "📚 KONU BAZLI HATA KİTAPÇIĞI (PDF)",
            "📅 Günlük Ödev Takip & WhatsApp", 
            "👥 Sınıf Listesi Yönetimi"
        ])
        
        # ----------------------------------------------------
        # SEKME 1: İNCELENMEMİŞ HATA BİLDİRİMLERİ
        # ----------------------------------------------------
        with sekme1:
            st.header("🔍 Yeni Yüklenen Öğrenci Soruları")
            gelen_sorular = supabase.table("student_errors").select("*").eq("is_checked", False).order("created_at", desc=True).execute()
            
            if gelen_sorular.data:
                for idx, s in enumerate(gelen_sorular.data):
                    col_sol, col_sag = st.columns([4, 1])
                    with col_sol:
                        st.write(f"👤 **Öğrenci:** {s['student_name']} | 🔸 **Konu:** {s['topic_name']} | 📌 **Durum:** {s['error_type']}")
                        st.image(s['image_url'], width=300)
                    with col_sag:
                        if st.button("✓ İnceledim / Arşivle", key=f"ok_{s['id']}"):
                            supabase.table("student_errors").update({"is_checked": True}).eq("id", s["id"]).execute()
                            st.rerun()
                    st.write("---")
            else:
                st.success("🎉 Harika! İncelenmemiş yeni soru bulunmuyor.")

        # ----------------------------------------------------
        # SEKME 2: PDF HATA KİTAPÇIĞI OLUŞTURUCU
        # ----------------------------------------------------
        with sekme2:
            st.header("📚 Konu Bazlı Tarama Kitapçığı")
            st.write("Seçtiğiniz öğrenci ve konuya ait tüm soruları tek tıkla **PDF** yapın.")
            
            tum_hatalar = supabase.table("student_errors").select("student_name, topic_name").execute()
            if tum_hatalar.data:
                mevcut_ogrenciler = list(set([h["student_name"] for h in tum_hatalar.data]))
                
                c_o, c_k = st.columns(2)
                with c_o: sec_o = st.selectbox("Öğrenci Seçin:", mevcut_ogrenciler, key="pdf_o")
                
                # Seçilen öğrencinin yüklediği konuları filtrele
                ogrenci_konulari = list(set([h["topic_name"] for h in tum_hatalar.data if h["student_name"] == sec_o]))
                
                with c_k: sec_k = st.selectbox("Konu Seçin:", ogrenci_konulari, key="pdf_k")
                
                if st.button("🔍 Soru Verilerini Topla ve PDF Hazırla"):
                    soru_kayitlari = supabase.table("student_errors").select("*")\
                        .eq("student_name", sec_o)\
                        .eq("topic_name", sec_k)\
                        .execute()
                    
                    if soru_kayitlari.data:
                        gorsel_listesi = [{"url": item["image_url"], "durum": item["error_type"]} for item in soru_kayitlari.data]
                        
                        pdf_buffer = pdf_olustur(sec_o, sec_k, gorsel_listesi)
                        dosya_adi = dosya_adi_temizle(f"{sec_o}-{sec_k}-Hata-Fasikulu.pdf")
                        
                        st.success(f"🎉 Toplam {len(gorsel_listesi)} adet soru toplandı!")
                        st.download_button(
                            label="📥 KONU TARAMA FASİKÜLÜNÜ İNDİR (PDF)",
                            data=pdf_buffer,
                            file_name=dosya_adi,
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.write("---")
                        st.subheader("🖼️ Soru Önizlemeleri")
                        cols = st.columns(3)
                        for i, g in enumerate(gorsel_listesi):
                            with cols[i % 3]:
                                st.caption(f"📌 {g['durum']}")
                                st.image(g['url'], use_container_width=True)
                    else:
                        st.warning("Bu konuda yüklenmiş soru bulunamadı.")
            else:
                st.info("Sistemde henüz yüklenmiş soru bulunmuyor.")

        # ----------------------------------------------------
        # SEKME 3: GÜNLÜK ÖDEV TAKİP & WHATSAPP
        # ----------------------------------------------------
        with sekme3:
            st.header("📅 Günlük Ödev Kontrol Tablosu")
            secilen_tarih = st.date_input("Kontrol Tarihi:", datetime.today())
            tarih_str = secilen_tarih.strftime("%Y-%m-%d")
            
            if not tum_ogrenciler:
                st.warning("Lütfen önce sınıf listenize öğrenci ekleyin.")
            else:
                st.subheader("✉️ WhatsApp Mesaj Taslağı")
                varsayilan_mesaj = "Math Pie sisteminde bugün yapman gereken soru/hata girişi eksik görünmektedir. Lütfen gün bitmeden eksiklerini tamamla! 🥧"
                taslak_mesaj = st.text_area("Mesaj Taslağı:", value=varsayilan_mesaj, height=80)
                st.write("---")
                
                # Bugün soru yükleyen öğrenciler
                bugun_kayit = supabase.table("student_errors").select("student_name").gte("created_at", f"{tarih_str}T00:00:00").lte("created_at", f"{tarih_str}T23:59:59").execute()
                yapanlar = list(set([b["student_name"] for b in bugun_kayit.data])) if bugun_kayit.data else []
                
                col_y, col_yap = st.columns(2)
                with col_y:
                    st.subheader(f"🟢 Giriş Yapanlar ({len(yapanlar)})")
                    for y in yapanlar:
                        st.write(f"✅ {y}")
                        
                with col_yap:
                    st.subheader("🔴 Giriş Yapmayanlar")
                    ogrenci_tel_map = {o["student_name"]: o.get("student_phone", "") for o in ogrenciler_data}
                    
                    yapmayan_sayisi = 0
                    for ogrenci in tum_ogrenciler:
                        if ogrenci not in yapanlar:
                            yapmayan_sayisi += 1
                            c_isim, c_btn = st.columns([2, 1])
                            with c_isim:
                                st.write(f"❌ {ogrenci}")
                            with c_btn:
                                mesaj = f"Merhaba {ogrenci},\n\n{taslak_mesaj}"
                                kodlanmis = urllib.parse.quote(mesaj)
                                tel = str(ogrenci_tel_map.get(ogrenci, "")).strip()
                                
                                if tel and tel != "None":
                                    if tel.startswith("0"): tel = "90" + tel[1:]
                                    elif not tel.startswith("90"): tel = "90" + tel
                                    wa_url = f"https://wa.me/{tel}?text={kodlanmis}"
                                else:
                                    wa_url = f"https://wa.me/?text={kodlanmis}"
                                    
                                st.markdown(f'[@button Hatırlat 💬]({wa_url})', unsafe_allow_html=True)
                                
                    if yapmayan_sayisi == 0:
                        st.success("🎉 Harika! Bugün tüm öğrenciler eksiksiz giriş yaptı.")

        # ----------------------------------------------------
        # SEKME 4: SINIF LİSTESİ YÖNETİMİ
        # ----------------------------------------------------
        with sekme4:
            st.header("👥 Sınıf ve Öğrenci Yönetimi")
            
            st.subheader("➕ Yeni Öğrenci Ekle")
            c_e1, c_e2, c_e3, c_e4 = st.columns(4)
            with c_e1: y_ad = st.text_input("Ad Soyad:")
            with c_e2: y_num = st.text_input("Öğrenci No:")
            with c_e3: y_sifre = st.text_input("Giriş Şifresi:")
            with c_e4: y_tel = st.text_input("Veli/Öğrenci Tel (Örn: 05xx):")
            
            if st.button("Öğrenciyi Kaydet"):
                if y_ad and y_sifre:
                    supabase.table("student_list").insert({
                        "student_name": y_ad, 
                        "student_number": y_num, 
                        "student_password": y_sifre,
                        "student_phone": y_tel
                    }).execute()
                    st.success(f"'{y_ad}' başarıyla eklendi!")
                    st.rerun()
                else:
                    st.warning("Ad Soyad ve Şifre alanları zorunludur.")
                    
            st.write("---")
            st.subheader("📋 Kayıtlı Öğrenci Listesi")
            if ogrenciler_data:
                for o in ogrenciler_data:
                    c_l1, c_l2 = st.columns([5, 1])
                    with c_l1:
                        st.write(f"👤 **{o['student_name']}** | No: {o.get('student_number', '-')} | Şifre: {o.get('student_password', '-')} | Tel: {o.get('student_phone', '-')}")
                    with c_l2:
                        if st.button("Sil 🗑️", key=f"sil_o_{o['id']}"):
                            supabase.table("student_list").delete().eq("id", o["id"]).execute()
                            st.rerun()
            else:
                st.info("Kayıtlı öğrenci bulunmuyor.")

    elif hocam_sifre != "":
        st.error("❌ Hatalı Yönetici Şifresi!")
