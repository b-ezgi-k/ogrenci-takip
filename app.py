import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import plotly.express as px
import pandas as pd
import requests
from io import BytesIO
import urllib.parse  # 🔗 WhatsApp linklerini güvenli şifrelemek için eklendi

# PDF Üretimi İçin Gerekli ReportLab Kitaplıkları
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Supabase bağlantı bilgilerimiz
SUPABASE_URL = "https://aasptqqypnshuanmwbko.supabase.co"
SUPABASE_KEY = "sb_publishable_ILbUCJ_olLbcV13gabNOdQ_1g66fh2U"

# 🔑 Sadece sizin bileceğiniz Ana Öğretmen Şifresi
OGRETMEN_ANA_SIFRESI = "MathPie2026"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛠️ TÜRKÇE KARAKTER VE BOŞLUK TEMİZLEME FONKSİYONU
def dosya_adi_temizle(metin):
    turkce_karakterler = {"ç": "c", "ğ": "g", "ı": "i", "i": "i", "ö": "o", "ş": "s", "ü": "u", "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U"}
    for kaynak, hedef in turkce_karakterler.items():
        metin = metin.replace(kaynak, hedef)
    metin = metin.replace(" ", "-")
    return metin.lower()

# 📑 ARKA PLANDA GERÇEK PDF ÜRETME FONKSİYONU (YÜKSEKLİK HATASI ENGELLENMİŞ SÜRÜM)
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
        alignment=1, # Center
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
            response = requests.get(oge['url'])
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

# Ortak Veri Çekme İşlemleri
kitaplar_data = supabase.table("books").select("id", "book_name").execute()
kitap_id_to_name = {k["id"]: k["book_name"] for k in kitaplar_data.data} if kitaplar_data.data else {}

# 👥 Öğrenci listesini ve tüm ham verileri öğretmen takibi için çekiyoruz
ogrenciler_data = supabase.table("student_list").select("*").execute()
tum_ogrenciler = [o["student_name"] for o in ogrenciler_data.data] if ogrenciler_data.data else []

# ==========================================
# ÖĞRETMEN PANELİ (ŞİFRE KORUMALI)
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
        
        # SEKME 1: YENİ GELEN BİLDİRİMLER
        with sekme1:
            st.header("🔍 İncelenmemiş Öğrenci Hataları")
            yeni_sonuclar = supabase.table("student_results").select("*").eq("is_checked", False).execute()
            
            if yeni_sonuclar.data:
                for rapor in yeni_sonuclar.data:
                    test_bilgi = supabase.table("tests").select("test_name", "total_questions", "subject_id").eq("id", rapor["test_id"]).execute()
                    if test_bilgi.data:
                        t_adi = test_bilgi.data[0]["test_name"]
                        t_soru_sayisi = test_bilgi.data[0]["total_questions"]
                        s_id = test_bilgi.data[0]["subject_id"]
                        
                        konu_bilgi = supabase.table("subjects").select("subject_name", "book_id").eq("id", s_id).execute()
                        if konu_bilgi.data:
                            konu_adi = konu_bilgi.data[0]["subject_name"]
                            b_id = konu_bilgi.data[0]["book_id"]
                            kitap_adi = kitap_id_to_name.get(b_id, "Bilinmeyen Kitap")
                            
                            raw_w = rapor["wrong_questions"]
                            if "http" in raw_w:
                                eksik_adet = len(raw_w.split("|||"))
                                gosterge = f"📸 {eksik_adet} Yapılamayan Soru Yüklendi"
                            else:
                                yanlislar = [int(x.strip()) for x in raw_w.split(",") if x.strip().isdigit()] if raw_w else []
                                boslar = [int(x.strip()) for x in rapor["blank_questions"].split(",") if x.strip().isdigit()] if rapor["blank_questions"] else []
                                eksik_adet = len(yanlislar) + len(boslar)
                                gosterge = f"Eski Kayıt ({eksik_adet} Hata)"
                            
                            dogru_sayisi = t_soru_sayisi - eksik_adet
                            basari_yuzdesi = int((dogru_sayisi / t_soru_sayisi) * 100) if t_soru_sayisi > 0 else 0
                            
                            r_sol, r_sag = st.columns([4, 1])
                            with r_sol:
                                st.write(f"👤 **Öğrenci:** {rapor['student_name']} | 📖 **{kitap_adi}** | 🔸 **{konu_adi}** | 📝 {t_adi} | 🎯 **Başarı:** %{basari_yuzdesi} ({gosterge})")
                            with r_sag:
                                if st.button("✓ Kontrol Edildi", key=f"check_{rapor['id']}"):
                                    supabase.table("student_results").update({"is_checked": True}).eq("id", rapor["id"]).execute()
                                    st.success("Test arşivlendi!")
                                    st.rerun()
                            st.write("---")
            else:
                st.success("🎉 Harika! İncelenmemiş hiç ödev/test bilgilendirmesi kalmadı.")
                
        # SEKME 2: KONU BAZLI HATA KİTAPÇIĞI
        with sekme2:
            st.header("📚 Konu Bazlı Tarama Kitapçığı")
            st.write("Öğrencinin geçmişte yüklediği tüm yanlış ve boş soruları filtreleyip hakiki bir PDF dosyası olarak indirebilirsiniz.")
            
            if tum_ogrenciler:
                c_k1, c_k2, c_k3 = st.columns(3)
                with c_k1: t_ogrenci = st.selectbox("1. Öğrenci Seçin:", tum_ogrenciler, key="tarama_o")
                with c_k2: t_kitap = st.selectbox("2. Kitap Seçin:", list(kitap_id_to_name.values()), key="tarama_k")
                
                selected_book_id = [k for k, v in kitap_id_to_name.items() if v == t_kitap][0]
                konuorlar_db = supabase.table("subjects").select("id", "subject_name").eq("book_id", selected_book_id).execute()
                
                if konuorlar_db.data:
                    konu_haritasi_tarama = {k["subject_name"]: k["id"] for k in konuorlar_db.data}
                    with c_k3: t_konu = st.selectbox("3. Konu Seçin:", list(konu_haritasi_tarama.keys()), key="tarama_konu")
                    
                    if st.button("🔍 Tarama Verilerini Topla"):
                        secilen_konu_id = konu_haritasi_tarama[t_konu]
                        testler_db = supabase.table("tests").select("id", "test_name").eq("subject_id", secilen_konu_id).execute()
                        test_idleri = [t["id"] for t in testler_db.data] if testler_db.data else []
                        
                        if test_idleri:
                            ogrenci_raporlari = supabase.table("student_results").select("*").eq("student_name", t_ogrenci).in_("test_id", test_idleri).execute()
                            
                            gorsel_listesi = []
                            if ogrenci_raporlari.data:
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
                        else: st.warning("Bu konuya ait henüz sistemde tanımlı bir test bulunmuyor.")
                else: st.warning("Bu kitaba ait henüz bir konu bulunmuyor.")

        # SEKME 3: GÜNLÜK ÖDEV TAKİP RAPORU & ESNEK WHATSAPP SİSTEMİ
        with sekme3:
            st.header("📅 Günlük Ödev Durum Tablosu")
            secilen_tarih = st.date_input("Hangi Günün Ödev Kontrolünü Görmek İstersiniz?", datetime.today())
            tarih_str = secilen_tarih.strftime("%Y-%m-%d")
            
            if len(tum_ogrenciler) == 0:
                st.warning("Bu raporun çalışabilmesi için önce 'Sınıf Listesi Yönetimi' sekmesinden öğrencilerini eklemelisiniz.")
            else:
                # 📝 Dinamik Mesaj Taslağı Düzenleme Kutusu
                st.write("---")
                st.subheader("✉️ Günlük WhatsApp Hatırlatma Mesajı Taslağı")
                varsayilan_mesaj = "Math Pie sisteminde bugün yapman gereken ödev/hata girişi eksik görünmektedir. Sürecinin aksamaması için gün bitmeden eksiklerini tamamlamanı bekliyorum. İyi çalışmalar! 🥧"
                
                taslak_mesaj = st.text_area(
                    "Mesajınızı özelleştirebilirsiniz (Öğrencinin ismi otomatik olarak en başa eklenecektir):", 
                    value=varsayilan_mesaj,
                    height=100,
                    key="dinamik_taslak_input"
                )
                st.write("---")

                # Bugün ödev gönderen kayıtları çek
                bugun_gonderenler_data = supabase.table("student_results").select("student_name").gte("created_at", f"{tarih_str}T00:00:00").lte("created_at", f"{tarih_str}T23:59:59").execute()
                yapanlar = list(set([b["student_name"] for b in bugun_gonderenler_data.data])) if bugun_gonderenler_data.data else []
                
                g_sol, g_sag = st.columns(2)
                with g_sol:
                    st.subheader(f"🟢 Ödevini Yapanlar ({len(yapanlar)})")
                    for y_ogrenci in yapanlar: 
                        st.write(f"✅ {y_ogrenci}")
                        
                with g_sag:
                    st.subheader(f"🔴 Ödevini Yapmayanlar")
                    
                    # Veri tabanından telefonları eşleştirmek için öğrenci bilgilerini sözlüğe alıyoruz
                    # Eğer tablonuzda 'student_phone' veya benzeri bir ad varsa ona göre güncellenebilir, şimdilik güvenli get yapısı kuruldu
                    ogrenci_telefon_haritasi = {o["student_name"]: o.get("student_phone", "") for o in ogrenciler_data.data} if ogrenciler_data.data else {}
                    
                    yapmayan_sayisi = 0
                    for yap_ogrenci in tum_ogrenciler:
                        if yap_ogrenci not in yapanlar:
                            yapmayan_sayisi += 1
                            col_isim, col_buton = st.columns([2, 1])
                            
                            with col_isim:
                                st.write(f"❌ {yap_ogrenci}")
                                
                            with col_buton:
                                # Kişiye özel mesajı oluşturuyoruz
                                tam_mesaj = f"Merhaba {yap_ogrenci},\n\n{taslak_mesaj}"
                                kodlanmis_mesaj = urllib.parse.quote(tam_mesaj)
                                
                                # Öğrencinin telefon numarasını al ve temizle
                                ham_tel = str(ogrenci_telefon_haritasi.get(yap_ogrenci, "")).strip()
                                
                                # Eğer sistemde telefon yoksa veya boşsa, öğretmen manuel numara girsin diye boş wa.me açılır
                                if ham_tel == "" or ham_tel == "None":
                                    whatsapp_linki = f"https://wa.me/?text={kodlanmis_mesaj}"
                                else:
                                    if ham_tel.startswith("0"):
                                        ham_tel = "90" + ham_tel[1:]
                                    elif not ham_tel.startswith("90"):
                                        ham_tel = "90" + ham_tel
                                    whatsapp_linki = f"https://wa.me/{ham_tel}?text={kodlanmis_mesaj}"
                                
                                # Küçük, şık ve yan yana duran bir buton linki üretiyoruz
                                st.markdown(f'[@button Hatırlat 💬]({whatsapp_linki})', unsafe_allow_html=True)
                    
                    if yapmayan_sayisi == 0:
                        st.empty()
                        st.success("Harika! Bugün tüm sınıf ödev girişlerini tıkır tıkır tamamladı. 🎉")

        # SEKME 4: GRAFİKLER SEKMESİ
        with sekme4:
            st.header("📈 Akıllı Grafik Analizleri")
            tum_sonuclar = supabase.table("student_results").select("*").order("created_at").execute()
            
            if not tum_sonuclar.data or len(tum_ogrenciler) == 0:
                st.info("Grafiklerin çizilebilmesi için sistemde öğrenci ve gönderilmiş test sonucu olması gerekir.")
            else:
                secilen_grafik_ogrencisi = st.selectbox("Grafiğini Görmek İstediğiniz Öğrenciyi Seçin:", tum_ogrenciler, key="g_o")
                
                grafik_listesi = []
                for r in tum_sonuclar.data:
                    if r["student_name"] == secilen_grafik_ogrencisi:
                        t_bilgi = supabase.table("tests").select("test_name", "total_questions", "subject_id").eq("id", r["test_id"]).execute()
                        if t_bilgi.data:
                            t_adi = t_bilgi.data[0]["test_name"]
                            t_soru = t_bilgi.data[0]["total_questions"]
                            s_id = t_bilgi.data[0]["subject_id"]
                            
                            k_bilgi = supabase.table("subjects").select("subject_name", "book_id").eq("id", s_id).execute()
                            if k_bilgi.data:
                                konu_adi = k_bilgi.data[0]["subject_name"]
                                b_id = k_bilgi.data[0]["book_id"]
                                
                                kitap_bilgi = supabase.table("books").select("book_name").eq("id", b_id).execute()
                                kitap_adi = kitap_bilgi.data[0]["book_name"] if kitap_bilgi.data else "Bilinmeyen Kitap"
                                
                                raw_w = r["wrong_questions"]
                                if "http" in raw_w:
                                    eksik_sayi = len(raw_w.split("|||"))
                                else:
                                    y_sayi = len([int(x) for x in raw_w.split(",") if x.strip().isdigit()]) if raw_w else 0
                                    b_sayi = len([int(x) for x in r["blank_questions"].split(",") if x.strip().isdigit()]) if r["blank_questions"] else 0
                                    eksik_sayi = y_sayi + b_sayi
                                    
                                dogru = t_soru - eksik_sayi
                                yuzde = int((dogru / t_soru) * 100) if t_soru > 0 else 0
                                
                                grafik_listesi.append({
                                    "Kitap": kitap_adi, "Konu": konu_adi, "Test": t_adi, "Toplam Soru": t_soru,
                                    "Dogru Soru": dogru, "Başarı Yüzdesi": yuzde, "Kitap - Test Adı": f"{kitap_adi} / {t_adi}"
                                })
                
                if len(grafik_listesi) > 0:
                    df_raw = pd.DataFrame(grafik_listesi)
                    df_grouped = df_raw.groupby(["Kitap", "Konu"]).agg({"Toplam Soru": "sum", "Dogru Soru": "sum"}).reset_index()
                    df_grouped["Genel Başarı Yüzdesi"] = ((df_grouped["Dogru Soru"] / df_grouped["Toplam Soru"]) * 100).astype(int)
                    
                    st.write("---")
                    st.subheader("📚 Kitap Bazlı Genel Konu Başarı Karşılaştırması")
                    mevcut_konular = df_grouped["Konu"].unique()
                    secilen_grafik_konusu = st.selectbox("Hangi Konunun Kitap Karşılaştırmasını Görmek İstersiniz?", mevcut_konular)
                    
                    df_konu = df_grouped[df_grouped["Konu"] == secilen_grafik_konusu]
                    fig_karsilastirma = px.bar(df_konu, x="Kitap", y="Genel Başarı Yüzdesi", color="Kitap", text="Genel Başarı Yüzdesi", range_y=[0, 105])
                    st.plotly_chart(fig_karsilastirma, use_container_width=True)
                else: st.warning("Grafik çizilecek yeterli veri yok.")

        # SEKME 5: SINIF VE MÜFREDAT YÖNETİMİ
        with sekme5:
            st.header("👥 Sınıf Listesi ve Kitap Atama")
            
            st.subheader("➕ Yeni Öğrenci Ekle")
            c_ekle1, c_ekle2, c_ekle3 = st.columns(3)
            with c_ekle1: y_ad = st.text_input("Ad Soyad:")
            with c_ekle2: y_num = st.text_input("Okul / Giriş Numarası:")
            with c_ekle3: y_sifre = st.text_input("Giriş Şifresi:", type="password")
                
            if st.button("Öğrenciyi Kaydet"):
                if y_ad and y_num and y_sifre:
                    supabase.table("student_list").insert({"student_name": y_ad, "student_number": y_num, "student_password": y_sifre}).execute()
                    st.success(f"'{y_ad}' başarıyla eklendi!")
                    st.rerun()
            
            st.write("---")
            st.subheader("🎯 Öğrenciye Özel Kitap Atama Paneli")
            if tum_ogrenciler and kitaplar_data.data:
                c1, c2 = st.columns(2)
                with c1: secilen_atama_ogrencisi = st.selectbox("Öğrenci Seçin:", tum_ogrenciler, key="atama_o")
                with c2: secilen_atama_kitabi = st.selectbox("Tanımlanacak Kitabı Seçin:", list(kitap_id_to_name.values()), key="atama_k")
                
                if st.button("Kitabı Bu Öğrenciye Tanımla"):
                    k_id = [k for k, v in kitap_id_to_name.items() if v == secilen_atama_kitabi][0]
                    supabase.table("student_book_assignments").insert({"student_name": secilen_atama_ogrencisi, "book_id": k_id}).execute()
                    st.success("Kitap başarıyla atandı!")
                    st.rerun()

            st.write("---")
            st.header("📚 Mevcut Müfredat Yapısı ve Veri Ekleme/Silme")
            if kitaplar_data.data:
                for kitap in kitaplar_data.data:
                    ks_l, ks_r = st.columns([5, 1])
                    with ks_l: st.subheader(f"📖 {kitap['book_name']}")
                    with ks_r:
                        if st.button("Kitabı Sil 🗑️", key=f"sil_k_{kitap['id']}"):
                            supabase.table("books").delete().eq("id", kitap["id"]).execute(); st.rerun()
                            
                    konular_data = supabase.table("subjects").select("id", "subject_name").eq("book_id", kitap["id"]).execute()
                    if konular_data.data:
                        for konu in konular_data.data:
                            kons_l, kons_r = st.columns([5, 1])
                            with kons_l: st.markdown(f"**&nbsp;&nbsp;&nbsp;&nbsp;🔸 {konu['subject_name']}**")
                            with kons_r:
                                if st.button("Konuyu Sil 🗑️", key=f"sil_kon_{konu['id']}"):
                                    supabase.table("subjects").delete().eq("id", konu["id"]).execute(); st.rerun()
                                    
                            testler_data = supabase.table("tests").select("id", "test_name", "total_questions").eq("subject_id", konu["id"]).execute()
                            if testler_data.data:
                                for test in testler_data.data:
                                    ts_l, ts_r = st.columns([5, 1])
                                    with ts_l: st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;📝 {test['test_name']} ({test['total_questions']} Soru)")
                                    with ts_r:
                                        if st.button("Testi Sil 🗑️", key=f"sil_t_{test['id']}"):
                                            supabase.table("tests").delete().eq("id", test['id']).execute(); st.rerun()
            
            st.write("---")
            st.subheader("➕ 1. Yeni Kitap Ekle")
            y_kitap = st.text_input("Kitap Adı Yazın (Örn: 345 Matematik):", key="ekle_k_input")
            if st.button("Kitabı Kaydet"):
                if y_kitap: supabase.table("books").insert({"book_name": y_kitap}).execute(); st.rerun()
            
            if kitaplar_data.data:
                st.write("---")
                st.subheader("➕ 2. Yeni Konu Ekle")
                k_secim_listesi = {k["book_name"]: k["id"] for k in kitaplar_data.data}
                secilen_konu_kitabi = st.selectbox("Hangi Kitaba Konu Eklemek İstersiniz?", list(k_secim_listesi.keys()), key="konu_k_sec")
                y_konu = st.text_input("Konu Adı Yazın (Örn: Fonksiyonlar):", key="ekle_konu_input")
                if st.button("Konuyu Kaydet"):
                    if y_konu: supabase.table("subjects").insert({"subject_name": y_konu, "book_id": k_secim_listesi[secilen_konu_kitabi]}).execute(); st.rerun()

                st.write("---")
                st.subheader("➕ 3. Yeni Test Ekle")
                secilen_test_kitabi = st.selectbox("Test Hangi Kitapta?", list(k_secim_listesi.keys()), key="test_k_sec")
                aktif_konular = supabase.table("subjects").select("id", "subject_name").eq("book_id", k_secim_listesi[secilen_test_kitabi]).execute()
                if aktif_konular.data:
                    konu_secim_listesi = {kon["subject_name"]: kon["id"] for kon in aktif_konular.data}
                    secilen_test_konusu = st.selectbox("Test Hangi Konuya Ait?", list(konu_secim_listesi.keys()), key="test_konu_sec")
                    
                    c_t1, c_t2 = st.columns(2)
                    with c_t1: y_test_adi = st.text_input("Test Adı (Örn: Test 1):", key="ekle_test_input")
                    with c_t2: y_test_soru = st.number_input("Toplam Soru Sayısı:", min_value=1, max_value=100, value=12, key="ekle_soru_input")
                        
                    if st.button("Testi Kaydet"):
                        if y_test_adi: supabase.table("tests").insert({"test_name": y_test_adi, "total_questions": int(y_test_soru), "subject_id": konu_secim_listesi[secilen_test_konusu]}).execute(); st.rerun()
            
    elif hocam_sifre != "": st.error("❌ Hatalı Yönetici Şifresi!")

# ==========================================
# ÖĞRENCİ PANELİ
# ==========================================
else:
    st.title("🎯 Öğrenci Soru/Hata Bildirim Ekranı")
    st.write("---")
    
    g_numara = st.text_input("Öğrenci Numaranız:")
    g_sifre = st.text_input("Giriş Şifreniz:", type="password")
    
    if g_numara and g_sifre:
        dogrulama = supabase.table("student_list").select("*").eq("student_number", g_numara).eq("student_password", g_sifre).execute()
        
        if dogrulama.data:
            ogrenci_adi = dogrulama.data[0]["student_name"]
            st.success(f"✅ Hoş geldin, {ogrenci_adi}!")
            
            o_sekme1, o_sekme2 = st.tabs(["📝 Yeni Ödev Bildirimi Gönder", "⏱️ Çözdüğüm Testler Geçmişi"])
            
            cozulmus_testler_data = supabase.table("student_results").select("*").eq("student_name", ogrenci_adi).execute()
            cozulmus_test_idleri = [r["test_id"] for r in cozulmus_testler_data.data] if cozulmus_testler_data.data else []
            
            with o_sekme1:
                ogrenci_atamalari = supabase.table("student_book_assignments").select("book_id").eq("student_name", ogrenci_adi).execute()
                atanan_kitap_idleri = [a["book_id"] for a in ogrenci_atamalari.data] if ogrenci_atamalari.data else []
                ogrenci_kitap_listesi = {k["book_name"]: k["id"] for k in kitaplar_data.data if k["id"] in atanan_kitap_idleri}
                
                if ogrenci_kitap_listesi:
                    secilen_kitap = st.selectbox("1. Kitap Seçin", list(ogrenci_kitap_listesi.keys()))
                    konular = supabase.table("subjects").select("id", "subject_name").eq("book_id", ogrenci_kitap_listesi[secilen_kitap]).execute()
                    
                    if konular.data:
                        konu_haritasi_o = {konu["subject_name"]: konu["id"] for konu in konular.data}
                        secilen_konu = st.selectbox("2. Konu Seçin", list(konu_haritasi_o.keys()))
                        
                        tum_testler = supabase.table("tests").select("id", "test_name", "total_questions").eq("subject_id", konu_haritasi_o[secilen_konu]).execute()
                        if tum_testler.data:
                            cozulmemis_testler = [t for t in tum_testler.data if t["id"] not in cozulmus_test_idleri]
                            
                            if cozulmemis_testler:
                                test_detay_haritasi = {f"{t['test_name']} ({t['total_questions']} Soru)": t for t in cozulmemis_testler}
                                secilen_test_etiket = st.selectbox("3. Test Seçin", list(test_detay_haritasi.keys()))
                                
                                secilen_test_objesi = test_detay_haritasi[secilen_test_etiket]
                                toplam_soru_adedi = secilen_test_objesi["total_questions"]
                                
                                soru_numaralari_listesi = list(range(1, toplam_soru_adedi + 1))
                                secilen_yanlislar = st.multiselect("🔴 YANLIŞ Yaptığınız Soru Numaraları:", soru_numaralari_listesi)
                                
                                kalan_sorular_bos_icin = [s for s in soru_numaralari_listesi if s not in secilen_yanlislar]
                                secilen_boslar = st.multiselect("🟡 BOŞ Bıraktığınız Soru Numaraları:", kalan_sorular_bos_icin)
                                
                                gorsel_linkleri_listesi = []
                                
                                if secilen_yanlislar or secilen_boslar:
                                    st.write("---")
                                    st.subheader("📸 Yapılamayan Soruların Fotoğraflarını Yükleyin")
                                    
                                    for y_soru in secilen_yanlislar:
                                        foto = st.file_uploader(f"📎 Yanlış - {y_soru}. Sorunun Fotoğrafı:", type=["png", "jpg", "jpeg"], key=f"foto_y_{y_soru}")
                                        if foto: gorsel_linkleri_listesi.append({"soru": f"Yanlış Soru {y_soru}", "dosya": foto, "kod": f"Y{y_soru}"})
                                        
                                    for b_soru in secilen_boslar:
                                        foto = st.file_uploader(f"📎 Boş - {b_soru}. Sorunun Fotoğrafı:", type=["png", "jpg", "jpeg"], key=f"foto_b_{b_soru}")
                                        if foto: gorsel_linkleri_listesi.append({"soru": f"Boş Soru {b_soru}", "dosya": foto, "kod": f"B{b_soru}"})
                                
                                if st.button("🚀 Test Sonucunu ve Tüm Fotoğrafları Öğretmenime Gönder"):
                                    final_urls = []
                                    temiz_ogrenci_adi = dosya_adi_temizle(ogrenci_adi)
                                    
                                    for oge in gorsel_linkleri_listesi:
                                        dosya_adi = f"{temiz_ogrenci_adi}_{secilen_test_objesi['id']}_{oge['kod']}.jpg"
                                        supabase.storage.from_("student-photos").upload(dosya_adi, oge["dosya"].getvalue(), {"content-type": "image/jpeg"})
                                        public_url = supabase.storage.from_("student-photos").get_public_url(dosya_adi)
                                        final_urls.append(f"{oge['soru']}::{public_url}")
                                    
                                    gorsel_metni = "|||".join(final_urls) if final_urls else "Görsel Yok"
                                    
                                    sonuc_verisi = {
                                        "student_name": ogrenci_adi, "test_id": secilen_test_objesi["id"],
                                        "wrong_questions": gorsel_metni, "blank_questions": "Fotoğraflı Yeni Sistem", "is_checked": False
                                    }
                                    supabase.table("student_results").insert(sonuc_verisi).execute()
                                    st.success("🎉 Ödeviniz başarıyla gönderildi!")
                                    st.rerun()
                            else: st.success("👏 Tüm testleri tamamladın.")
                else: st.warning("⚠️ Size tanımlanmış bir kitap bulunamadı.")
            
            with o_sekme2:
                st.header("⏱️ Çözüm ve Hata Geçmişin")
                if cozulmus_testler_data.data:
                    for g_rapor in cozulmus_testler_data.data:
                        g_test_bilgi = supabase.table("tests").select("test_name", "total_questions", "subject_id").eq("id", g_rapor["test_id"]).execute()
                        if g_test_bilgi.data:
                            gt_adi = g_test_bilgi.data[0]["test_name"]
                            durum_etiketi = "📥 İnceleniyor" if not g_rapor["is_checked"] else "✅ Kontrol Edildi"
                            st.write(f"📝 {gt_adi} | 📌 *{durum_etiketi}*")
                            
                            raw_wrong = g_rapor.get("wrong_questions", "")
                            if "http" in raw_wrong:
                                linkler = raw_wrong.split("|||")
                                for l in linkler:
                                    if "::" in l:
                                        u_bilgi, url = l.split("::")
                                        st.image(url, caption=f"Yüklediğin {u_bilgi}", width=250)
                            st.write("---")
