"""Green Edge Project — multilingual wildlife telemetry dashboard.

Expected input: live_feed.json in the working directory. Paths can be changed
with GREEN_EDGE_FEED_FILE and GREEN_EDGE_IMAGE_FOLDER environment variables.
"""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

st.set_page_config(
    page_title="Green Edge Wildlife Telemetry",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

FEED_FILE = Path(os.getenv("GREEN_EDGE_FEED_FILE", "live_feed.json"))
IMAGE_FOLDER = Path(os.getenv("GREEN_EDGE_IMAGE_FOLDER", "image_received"))
LIVE_IMAGE = IMAGE_FOLDER / "RARoom_live_progressive.jpg"
LOCAL_WILDLIFE_FOLDER = Path(os.getenv("GREEN_EDGE_WILDLIFE_FOLDER", "wildlife_images"))

LANGUAGES = {
    "English": "en",
    "Bahasa Indonesia": "id",
    "Basa Hulontalo": "gor",
}

# Basa Hulontalo has limited standardized vocabulary for telemetry terms.
# The Gorontalo copy below is deliberately plain and keeps technical loanwords.
# Please have a native speaker review it before public deployment.
UI = {
    "en": {
        "title": "Sustained 24/7 Wildlife Telemetry",
        "subtitle": "Near-real-time field monitoring • Green Edge Project",
        "language": "Interface language",
        "refresh": "Refresh interval",
        "last_update": "Last feed update",
        "online": "Receiver online",
        "delayed": "Feed delayed",
        "offline": "Receiver offline",
        "secure": "FIELD SYSTEM SECURE",
        "monitoring": "MONITORING ACTIVE",
        "active": "ACTIVE EVENT REGISTERED",
        "background": "BACKGROUND ENVIRONMENT EVENT",
        "receiving": "RECEIVING IMAGE STREAM",
        "live": "Live monitor",
        "events": "Event analytics",
        "guide": "Wildlife guide",
        "system": "System health",
        "packets": "Packets reassembled",
        "progress": "Transfer progress",
        "latency": "Packet reception timeline",
        "canvas": "Live progressive canvas",
        "no_packets": "No packet transit is currently recorded.",
        "waiting": "Waiting for a camera wake event.",
        "reconstructing": "Reconstructing incoming image",
        "snapshot": "Latest completed snapshot",
        "distribution": "Classification distribution",
        "records": "Classification records",
        "gallery": "Field capture archive",
        "no_history": "No classification history has been captured yet.",
        "no_archive": "The image archive is empty.",
        "search": "Search wildlife",
        "category": "Category",
        "all": "All",
        "representative": "Representative image",
        "image_note": "A local project image is preferred. The online image is a representative taxon photo.",
        "photo_unavailable": "Photo unavailable. Add a local image using the class ID as its filename.",
        "download": "Download event log (CSV)",
        "event_total": "Recorded events",
        "top_class": "Most frequent class",
        "confidence": "Latest confidence",
        "throughput": "Reception rate",
        "eta": "Estimated time remaining",
        "feed_age": "Feed age",
        "source": "Trigger source",
        "unknown": "Unknown",
        "localization_note": "Basa Hulontalo localization is a technical draft and should be reviewed by a native speaker.",
        "footer": "All rights reserved.",
    },
    "id": {
        "title": "Telemetri Satwa Liar 24/7",
        "subtitle": "Pemantauan lapangan mendekati waktu nyata • Green Edge Project",
        "language": "Bahasa antarmuka",
        "refresh": "Interval penyegaran",
        "last_update": "Pembaruan data terakhir",
        "online": "Penerima terhubung",
        "delayed": "Data terlambat",
        "offline": "Penerima tidak terhubung",
        "secure": "SISTEM LAPANGAN AMAN",
        "monitoring": "PEMANTAUAN AKTIF",
        "active": "KEJADIAN AKTIF TERDETEKSI",
        "background": "KEJADIAN LINGKUNGAN TERDETEKSI",
        "receiving": "MENERIMA ALIRAN GAMBAR",
        "live": "Monitor langsung",
        "events": "Analisis kejadian",
        "guide": "Panduan satwa",
        "system": "Kesehatan sistem",
        "packets": "Paket tersusun kembali",
        "progress": "Progres pengiriman",
        "latency": "Linimasa penerimaan paket",
        "canvas": "Kanvas progresif langsung",
        "no_packets": "Saat ini tidak ada perpindahan paket yang tercatat.",
        "waiting": "Menunggu kamera aktif karena pemicu.",
        "reconstructing": "Menyusun kembali gambar masuk",
        "snapshot": "Citra lengkap terbaru",
        "distribution": "Distribusi klasifikasi",
        "records": "Catatan klasifikasi",
        "gallery": "Arsip tangkapan lapangan",
        "no_history": "Belum ada riwayat klasifikasi yang direkam.",
        "no_archive": "Arsip gambar masih kosong.",
        "search": "Cari satwa",
        "category": "Kategori",
        "all": "Semua",
        "representative": "Gambar representatif",
        "image_note": "Gambar lokal proyek diutamakan. Gambar daring merupakan foto representatif takson.",
        "photo_unavailable": "Foto belum tersedia. Tambahkan gambar lokal dengan ID kelas sebagai nama file.",
        "download": "Unduh log kejadian (CSV)",
        "event_total": "Jumlah kejadian",
        "top_class": "Kelas terbanyak",
        "confidence": "Keyakinan terbaru",
        "throughput": "Laju penerimaan",
        "eta": "Perkiraan waktu tersisa",
        "feed_age": "Usia data",
        "source": "Sumber pemicu",
        "unknown": "Tidak diketahui",
        "localization_note": "Lokalisasi Basa Hulontalo adalah draf teknis dan perlu diperiksa oleh penutur asli.",
        "footer": "Seluruh hak cipta dilindungi.",
    },
    "gor": {
        "title": "Dasbor Telemetri Satwa Liar 24/7",
        "subtitle": "Pemantauan lo lapangi, dadata hampir waktu nyata • Green Edge Project",
        "language": "Basa antarmuka",
        "refresh": "Interval mopobaru",
        "last_update": "Data u paling bohu",
        "online": "Penerima tersambung",
        "delayed": "Data ma'o lambati",
        "offline": "Penerima dila tersambung",
        "secure": "SISTEM LO LAPANGI AMANI",
        "monitoring": "PEMANTAUAN AKTIF",
        "active": "KEJADIAN AKTIF TODETEKSI",
        "background": "KEJADIAN LINGKUNGAN TODETEKSI",
        "receiving": "MOTERIMA ALIRAN GAMBAR",
        "live": "Monitor langsung",
        "events": "Analisis kejadian",
        "guide": "Panduan satwa",
        "system": "Kondisi sistem",
        "packets": "Paket mopohutu kembali",
        "progress": "Progres pengiriman",
        "latency": "Waktu penerimaan paket",
        "canvas": "Gambar progresif langsung",
        "no_packets": "Wonu botiya dila data paket u motilanggula.",
        "waiting": "Mongohi kamera aktif.",
        "reconstructing": "Mopohutu kembali gambar u masuk",
        "snapshot": "Gambar lengkap u paling bohu",
        "distribution": "Distribusi klasifikasi",
        "records": "Catatan klasifikasi",
        "gallery": "Arsip gambar lo lapangi",
        "no_history": "Dila bo catatan klasifikasi.",
        "no_archive": "Arsip gambar masih kosong.",
        "search": "Lolohe satwa",
        "category": "Kategori",
        "all": "Todu-toduwa",
        "representative": "Gambar representatif",
        "image_note": "Gambar lokal proyek u utama. Gambar daring hanya foto representatif takson.",
        "photo_unavailable": "Foto dila bo. Tambahkan gambar lokal nganggo ID kelas sebagai nama file.",
        "download": "Unduh log kejadian (CSV)",
        "event_total": "Jumlah kejadian",
        "top_class": "Kelas terbanyak",
        "confidence": "Keyakinan terbaru",
        "throughput": "Laju penerimaan",
        "eta": "Perkiraan waktu tersisa",
        "feed_age": "Usia data",
        "source": "Sumber pemicu",
        "unknown": "Dila diketahui",
        "localization_note": "Lokalisasi Basa Hulontalo botiya masih draf teknis; minta penutur asli motolianga ulang.",
        "footer": "Todu-toduwa hak cipta dilindungi.",
    },
}

CATEGORIES = {
    "mammal": {"en": "Mammal", "id": "Mamalia", "gor": "Mamalia"},
    "bird": {"en": "Bird", "id": "Burung", "gor": "Manu"},
    "reptile": {"en": "Reptile", "id": "Reptil", "gor": "Reptil"},
    "human": {"en": "Human activity", "id": "Aktivitas manusia", "gor": "Aktivitas manusia"},
}

# "taxon" is used only to locate a representative licensed photo.
WILDLIFE = [
    {"id": "sulawesi_macaque", "en": "Sulawesi macaque", "id_name": "Monyet Sulawesi", "scientific": "Macaca spp.", "taxon": "Macaca hecki", "category": "mammal", "en_desc": "Sulawesi macaques are forest-dwelling primates found only on Sulawesi. They live socially, forage for fruit and other foods, and can be important seed dispersers; the classifier label may cover more than one regional Macaca species.", "id_desc": "Monyet Sulawesi adalah primata penghuni hutan yang hanya ditemukan di Sulawesi. Satwa sosial ini memakan buah dan pakan lain serta berperan dalam penyebaran biji; label model dapat mencakup lebih dari satu spesies Macaca di wilayah tersebut."},
    {"id": "maleo", "en": "Maleo", "id_name": "Maleo", "scientific": "Macrocephalon maleo", "taxon": "Macrocephalon maleo", "category": "bird", "en_desc": "The maleo is an endemic Sulawesi megapode that buries its unusually large eggs in sun-heated sand or geothermally warmed soil. Monitoring adults and nesting areas can help identify disturbance and protect breeding habitat.", "id_desc": "Maleo adalah burung megapoda endemik Sulawesi yang mengubur telurnya yang sangat besar pada pasir berpemanas matahari atau tanah hangat geotermal. Pemantauan individu dewasa dan lokasi bertelur membantu mengenali gangguan serta melindungi habitat reproduksi."},
    {"id": "lowland_anoa", "en": "Lowland anoa", "id_name": "Anoa dataran rendah", "scientific": "Bubalus depressicornis", "taxon": "Bubalus depressicornis", "category": "mammal", "en_desc": "The lowland anoa is a small, shy wild bovine endemic to Sulawesi. It generally uses forest with access to water and mineral sources, while camera-trap records can clarify occurrence in places where direct sightings are rare.", "id_desc": "Anoa dataran rendah adalah bovina liar berukuran kecil, pemalu, dan endemik Sulawesi. Satwa ini umumnya menggunakan hutan yang memiliki akses ke air dan sumber mineral; rekaman kamera jebak membantu memastikan keberadaannya saat perjumpaan langsung jarang terjadi."},
    {"id": "sulawesi_hornbill", "en": "Sulawesi hornbill", "id_name": "Kangkareng Sulawesi", "scientific": "Rhabdotorrhinus exarhatus", "taxon": "Rhabdotorrhinus exarhatus", "category": "bird", "en_desc": "The Sulawesi hornbill is an endemic fruit-eating forest bird. By moving seeds away from parent trees it contributes to forest regeneration, and its presence can indicate that suitable fruiting-tree habitat remains nearby.", "id_desc": "Kangkareng Sulawesi adalah burung hutan pemakan buah yang endemik Sulawesi. Perpindahan biji menjauhi pohon induk mendukung regenerasi hutan, sedangkan kemunculannya dapat menandakan masih tersedianya habitat dengan pohon pakan."},
    {"id": "gorontalo_tarsier", "en": "Gorontalo tarsier", "id_name": "Tarsius Gorontalo", "scientific": "Tarsius supriatnai", "taxon": "Tarsius supriatnai", "category": "mammal", "en_desc": "The Gorontalo or Jatna's tarsier is a small nocturnal primate described from the Gorontalo region. It hunts insects and other small prey, so night-time records and habitat context are especially useful for interpreting detections.", "id_desc": "Tarsius Gorontalo atau tarsius Jatna adalah primata nokturnal berukuran kecil yang dideskripsikan dari wilayah Gorontalo. Satwa ini memburu serangga dan mangsa kecil lain, sehingga rekaman malam hari serta konteks habitat penting untuk menafsirkan deteksinya."},
    {"id": "bear_cuscus", "en": "Sulawesi bear cuscus", "id_name": "Kuskus beruang Sulawesi", "scientific": "Ailurops ursinus", "taxon": "Ailurops ursinus", "category": "mammal", "en_desc": "The Sulawesi bear cuscus is an arboreal marsupial that moves slowly through the canopy and feeds largely on leaves. Canopy condition matters for this species, although ground cameras may record it when it descends or crosses low vegetation.", "id_desc": "Kuskus beruang Sulawesi adalah marsupial arboreal yang bergerak perlahan di tajuk dan terutama memakan daun. Kondisi tajuk penting bagi satwa ini, meskipun kamera di permukaan tanah dapat merekamnya saat turun atau melintasi vegetasi rendah."},
    {"id": "sulawesi_palm_civet", "en": "Sulawesi palm civet", "id_name": "Musang Sulawesi", "scientific": "Macrogalidia musschenbroekii", "taxon": "Macrogalidia musschenbroekii", "category": "mammal", "en_desc": "The Sulawesi palm civet is an endemic and mostly nocturnal carnivore that uses forested landscapes. Its secretive behaviour makes camera traps valuable for documenting activity times, distribution, and repeated use of trails.", "id_desc": "Musang Sulawesi adalah karnivora endemik yang terutama aktif malam hari dan menggunakan bentang alam berhutan. Perilakunya yang tersembunyi membuat kamera jebak berguna untuk merekam waktu aktivitas, sebaran, dan penggunaan jalur secara berulang."},
    {"id": "malay_civet", "en": "Malay civet", "id_name": "Tenggalung malaya", "scientific": "Viverra tangalunga", "taxon": "Viverra tangalunga", "category": "mammal", "en_desc": "The Malay civet is a nocturnal, ground-using mammal found across parts of Southeast Asia. It is adaptable in some modified habitats, and detections should be interpreted alongside site history because its occurrence on Sulawesi is linked to human-mediated introduction.", "id_desc": "Tenggalung malaya adalah mamalia nokturnal penghuni permukaan tanah yang tersebar di sebagian Asia Tenggara. Satwa ini dapat beradaptasi pada beberapa habitat termodifikasi; catatan di Sulawesi perlu dibaca bersama sejarah lokasi karena keberadaannya berkaitan dengan introduksi oleh manusia."},
    {"id": "sulawesi_babirusa", "en": "Sulawesi babirusa", "id_name": "Babirusa Sulawesi", "scientific": "Babyrousa celebensis", "taxon": "Babyrousa celebensis", "category": "mammal", "en_desc": "The Sulawesi babirusa is a distinctive endemic pig relative, with males developing curved upper tusks. It uses forest and wet areas, and repeated detections may reveal routes to feeding, wallowing, or mineral-lick locations.", "id_desc": "Babirusa Sulawesi adalah kerabat babi endemik yang khas; jantannya memiliki taring atas melengkung. Satwa ini menggunakan hutan dan area basah, sementara deteksi berulang dapat menunjukkan jalur menuju lokasi pakan, kubangan, atau sumber mineral."},
    {"id": "sulawesi_warty_pig", "en": "Sulawesi warty pig", "id_name": "Babi hutan Sulawesi", "scientific": "Sus celebensis", "taxon": "Sus celebensis", "category": "mammal", "en_desc": "The Sulawesi warty pig is endemic to Sulawesi and occupies a variety of natural and modified habitats. As an omnivore it can influence soil and vegetation through rooting, while camera records can reveal group size and activity patterns.", "id_desc": "Babi hutan Sulawesi merupakan satwa endemik yang menempati beragam habitat alami maupun termodifikasi. Sebagai omnivor, aktivitas mengoreknya dapat memengaruhi tanah dan vegetasi; rekaman kamera juga dapat menunjukkan ukuran kelompok dan pola aktivitas."},
    {"id": "timor_deer", "en": "Timor deer", "id_name": "Rusa timor", "scientific": "Rusa timorensis", "taxon": "Rusa timorensis", "category": "mammal", "en_desc": "Timor deer are medium-sized grazing and browsing deer native to parts of the Indonesian region and introduced elsewhere. Records can help track habitat use, herd composition, and possible interaction with people or cultivated areas.", "id_desc": "Rusa timor adalah rusa berukuran sedang yang merumput dan memakan pucuk; satwa ini asli di sebagian wilayah Indonesia dan diperkenalkan ke wilayah lain. Rekaman dapat membantu melacak penggunaan habitat, komposisi kelompok, serta interaksi dengan manusia atau area budidaya."},
    {"id": "rodent", "en": "Rodent", "id_name": "Rodensia", "scientific": "Rodentia", "taxon": "Muridae", "category": "mammal", "en_desc": "This broad class groups rats, mice, and other rodents that cannot yet be separated reliably by the model. Rodents have varied ecological roles as seed consumers, seed dispersers, prey, and habitat engineers, so species-level review is recommended when image quality permits.", "id_desc": "Kelas luas ini menggabungkan tikus dan rodensia lain yang belum dapat dipisahkan secara andal oleh model. Rodensia berperan sebagai pemakan atau penyebar biji, mangsa, dan pengubah mikrohabitat; pemeriksaan hingga tingkat spesies disarankan bila kualitas citra memungkinkan."},
    {"id": "sulawesi_squirrel", "en": "Sulawesi squirrel", "id_name": "Bajing Sulawesi", "scientific": "Sciuridae (Sulawesi taxa)", "taxon": "Prosciurillus murinus", "category": "mammal", "en_desc": "Sulawesi supports several endemic squirrels with different ranges and habitat preferences. This model class is intentionally broad; detections document small-mammal activity, but identification should be checked manually before assigning a species name.", "id_desc": "Sulawesi memiliki beberapa bajing endemik dengan sebaran dan pilihan habitat yang berbeda. Kelas model ini sengaja dibuat luas; deteksi menunjukkan aktivitas mamalia kecil, tetapi identifikasi perlu diperiksa secara manual sebelum menetapkan nama spesies."},
    {"id": "monitor_lizard", "en": "Monitor lizard", "id_name": "Biawak", "scientific": "Varanus spp.", "taxon": "Varanus salvator", "category": "reptile", "en_desc": "Monitor lizards are large, alert reptiles that forage for many kinds of animal food and carrion. Because this is a broad classifier class, body pattern, size, location, and habitat should be reviewed before deciding which Varanus species was recorded.", "id_desc": "Biawak adalah reptil besar dan waspada yang mencari beragam pakan hewani maupun bangkai. Karena kelas pengenal ini bersifat luas, pola tubuh, ukuran, lokasi, dan habitat perlu ditinjau sebelum menentukan spesies Varanus yang terekam."},
    {"id": "snake", "en": "Snake", "id_name": "Ular", "scientific": "Serpentes", "taxon": "Serpentes", "category": "reptile", "en_desc": "This class covers snakes visible in the camera frame and does not imply a species or danger level. Avoid inferring whether a snake is venomous from the automated label; retain the original image for expert verification.", "id_desc": "Kelas ini mencakup ular yang terlihat pada bingkai kamera dan tidak menunjukkan spesies maupun tingkat bahayanya. Jangan menyimpulkan apakah ular berbisa hanya dari label otomatis; simpan citra asli untuk verifikasi ahli."},
    {"id": "red_junglefowl", "en": "Red junglefowl", "id_name": "Ayam hutan merah", "scientific": "Gallus gallus", "taxon": "Gallus gallus", "category": "bird", "en_desc": "The red junglefowl is a ground-foraging forest-edge bird and a wild ancestor of domestic chickens. Camera images should be checked for domestic or hybrid traits, especially near settlements where free-ranging chickens may enter the monitoring area.", "id_desc": "Ayam hutan merah adalah burung pencari pakan di tanah yang sering menggunakan tepi hutan dan merupakan leluhur liar ayam domestik. Citra perlu diperiksa untuk ciri domestik atau hibrida, terutama dekat permukiman tempat ayam lepas dapat memasuki area pemantauan."},
    {"id": "philippine_megapode", "en": "Philippine megapode", "id_name": "Gosong Filipina", "scientific": "Megapodius cumingii", "taxon": "Megapodius cumingii", "category": "bird", "en_desc": "The Philippine megapode is a ground-dwelling bird that incubates eggs using heat from decomposing material or warm substrate rather than continuous parental brooding. Ground cameras can record foraging and movement near nesting habitat.", "id_desc": "Gosong Filipina adalah burung penghuni tanah yang mengerami telur dengan panas bahan organik membusuk atau substrat hangat, bukan dengan pengeraman induk secara terus-menerus. Kamera permukaan tanah dapat merekam aktivitas mencari makan dan pergerakan dekat habitat bersarang."},
    {"id": "sulawesi_ground_dove", "en": "Sulawesi ground dove", "id_name": "Delimukan Sulawesi", "scientific": "Gallicolumba tristigmata", "taxon": "Gallicolumba tristigmata", "category": "bird", "en_desc": "The Sulawesi ground dove is an endemic pigeon that spends much of its time walking and feeding on the forest floor. It can be difficult to observe directly, making trail-level camera records useful for documenting presence and activity.", "id_desc": "Delimukan Sulawesi adalah merpati endemik yang banyak berjalan dan mencari pakan di lantai hutan. Satwa ini sulit diamati secara langsung, sehingga rekaman kamera setinggi jalur berguna untuk mendokumentasikan keberadaan dan aktivitasnya."},
    {"id": "human", "en": "Human", "id_name": "Manusia", "scientific": "Homo sapiens", "taxon": "", "category": "human", "en_desc": "Human detections can indicate field-team visits or other activity near a camera. Access should be controlled because images may contain personal data; follow project consent, retention, and privacy procedures before displaying or sharing them.", "id_desc": "Deteksi manusia dapat menunjukkan kunjungan tim lapangan atau aktivitas lain di dekat kamera. Akses perlu dibatasi karena gambar dapat memuat data pribadi; ikuti prosedur persetujuan, retensi, dan privasi proyek sebelum menampilkan atau membagikannya."},
    {"id": "domestic_cat", "en": "Domestic cat", "id_name": "Kucing domestik", "scientific": "Felis catus", "taxon": "Felis catus", "category": "mammal", "en_desc": "Domestic cats may enter forest edges from nearby settlements or field stations. Their detection is worth tracking because free-ranging cats can interact with wildlife and may indicate human influence near the monitoring site.", "id_desc": "Kucing domestik dapat memasuki tepi hutan dari permukiman atau stasiun lapangan. Deteksinya perlu dicatat karena kucing yang berkeliaran dapat berinteraksi dengan satwa liar dan menandakan pengaruh manusia di sekitar lokasi pemantauan."},
    {"id": "gagang_bayam", "en": "Black-winged stilt", "id_name": "Gagang-bayam", "scientific": "Himantopus himantopus", "taxon": "Himantopus himantopus", "category": "bird", "en_desc": "The black-winged stilt is a long-legged waterbird that feeds in shallow wetlands, mudflats, and flooded areas. Detections can reflect local water conditions and the availability of open, shallow feeding habitat.", "id_desc": "Gagang-bayam adalah burung air berkaki panjang yang mencari makan di lahan basah dangkal, hamparan lumpur, dan area tergenang. Deteksinya dapat mencerminkan kondisi air setempat serta ketersediaan habitat makan yang terbuka dan dangkal."},
    {"id": "kuntul", "en": "Egret", "id_name": "Kuntul", "scientific": "Ardeidae", "taxon": "Egretta garzetta", "category": "bird", "en_desc": "This broad class covers white egrets that forage around water, grassland, or livestock. Plumage, bill and leg colour, size, and habitat should be checked manually because several egret species can appear similar in camera images.", "id_desc": "Kelas luas ini mencakup kuntul putih yang mencari makan di sekitar perairan, padang rumput, atau ternak. Warna bulu, paruh dan kaki, ukuran, serta habitat perlu diperiksa manual karena beberapa spesies kuntul tampak serupa pada citra kamera."},
]

# Draft Basa Hulontalo copy for the wildlife guide. Species names are retained
# where a verified, widely used local equivalent is not available.
GOR_NAMES = {
    "sulawesi_macaque": "Monyet Sulawesi",
    "maleo": "Manu Maleo",
    "lowland_anoa": "Anoa lo Dataran Rendah",
    "sulawesi_hornbill": "Kangkareng Sulawesi",
    "gorontalo_tarsier": "Tarsius Hulontalo",
    "bear_cuscus": "Kuskus Beruang Sulawesi",
    "sulawesi_palm_civet": "Musang Sulawesi",
    "malay_civet": "Tenggalung Malaya",
    "sulawesi_babirusa": "Babirusa Sulawesi",
    "sulawesi_warty_pig": "Babi Hutan Sulawesi",
    "timor_deer": "Rusa Timor",
    "rodent": "Rodensia",
    "sulawesi_squirrel": "Bajing Sulawesi",
    "monitor_lizard": "Biawak",
    "snake": "Ula",
    "red_junglefowl": "Manu Hutan Merah",
    "philippine_megapode": "Manu Gosong Filipina",
    "sulawesi_ground_dove": "Delimukan Sulawesi",
    "human": "Tawu",
    "domestic_cat": "Kucing Domestik",
    "gagang_bayam": "Manu Gagang-bayam",
    "kuntul": "Manu Kuntul",
}

GOR_DESC = {
    "sulawesi_macaque": "Monyet Sulawesi botiya primata u yilumulo to huta Sulawesi. Tiyombu hidup berkelompok, monga buah wawu makanan uwewo, boito mopomakmur penyebaran lo bini. Label model botiya mowali mencakup beberapa spesies Macaca to wilayah Sulawesi.",
    "maleo": "Manu maleo botiya manu endemik Sulawesi. Tiyombu molahu telur u damango to pasir u mohinggilo sababu matahari meyalo to buta u hangato sababu panas bumi. Pemantauan maleo wawu tampa molahu telur mowali membantu menjaga habitat reproduksi.",
    "lowland_anoa": "Anoa lo dataran rendah botiya binatangi liar u kiki, pemalu, wawu endemik Sulawesi. Tiyombu biasa yilumulo to huta u woluwo taluhu wawu sumber mineral. Kamera jebak membantu mololohu keberadaan anoa sababu jarang odelo langsung.",
    "sulawesi_hornbill": "Kangkareng Sulawesi botiya manu huta pemakan buah u endemik Sulawesi. Tiyombu membawa bini liyo-lio ode pohutu u boito membantu regenerasi huta. Wonu tiyombu terekam, boito mowali tanda woluwo habitat wawu pohutu buah to delomo wilayah.",
    "gorontalo_tarsier": "Tarsius Hulontalo meyalo tarsius Jatna botiya primata kiki u aktif hulondalo. Tiyombu monga serangga wawu binatangi kiki uwewo. Sababu boito, rekaman hulondalo wawu informasi habitat paralu ode menafsirkan hasil deteksi.",
    "bear_cuscus": "Kuskus beruang Sulawesi botiya marsupial u yilumulo to pohutu wawu bergerak mololo to tajuk huta. Makanan utama liyo daun. Kondisi tajuk paralu, bo kamera to buta mowali merekam wonu tiyombu mohuntu meyalo melintasi tanaman u odidi.",
    "sulawesi_palm_civet": "Musang Sulawesi botiya karnivora endemik u biasa aktif hulondalo wawu yilumulo to wilayah berhutan. Sababu sifat liyo u rahasia, kamera jebak berguna ode mololohu jam aktivitas, sebaran, wawu jalur u biasa dilalui.",
    "malay_civet": "Tenggalung malaya botiya mamalia hulondalo u yilumulo to buta wawu tersebar to beberapa wilayah Asia Tenggara. Tiyombu mowali beradaptasi to habitat u berubah. Rekaman to Sulawesi paralu dinilai wolo sejarah lokasi sababu keberadaan liyo berkaitan wolo introduksi lo tawu.",
    "sulawesi_babirusa": "Babirusa Sulawesi botiya kerabat babi endemik u khas; babirusa laki-laki woluwo taring hungo u melengkung. Tiyombu yilumulo to huta wawu tampa u basah. Deteksi berulang mowali motunggulo jalur ode tampa monga, kubangan, meyalo sumber mineral.",
    "sulawesi_warty_pig": "Babi hutan Sulawesi botiya binatangi endemik u yilumulo to habitat alami wawu habitat u telah berubah. Tiyombu monga macam-macam makanan wawu biasa mongore tanah. Rekaman kamera mowali motunggulo jumlah kelompok wawu pola aktivitas liyo.",
    "timor_deer": "Rusa Timor botiya rusa ukuran sedang u monga rumput wawu pucuk tanaman. Tiyombu asli to sebagian wilayah Indonesia wawu diperkenalkan to wilayah uwewo. Rekaman kamera membantu mololohu penggunaan habitat, kelompok, wawu interaksi wolo tawu meyalo kebun.",
    "rodent": "Kelas rodensia botiya mencakup tikus wawu rodensia uwewo u bo dila mowali dipisahkan model secara pasti. Rodensia mowali pemakan bini, penyebar bini, wawu makanan lo predator. Wonu gambar terang, identifikasi spesies paralu diperiksa ulang lo ahli.",
    "sulawesi_squirrel": "To Sulawesi woluwo beberapa bajing endemik wolo sebaran wawu habitat u berbeda. Kelas model botiya sengaja luas. Hasil deteksi motunggulo aktivitas mamalia kiki, bo nama spesies paralu diperiksa manual bohuliyo ditetapkan.",
    "monitor_lizard": "Biawak botiya reptil damango wawu waspada u monga berbagai binatangi kiki meyalo bangkai. Sababu kelas model botiya masih luas, pola badan, ukuran, lokasi, wawu habitat paralu diperiksa bohuliyo menentukan spesies Varanus.",
    "snake": "Kelas botiya mencakup ula u odelo to gambar kamera wawu dila langsung motunggulo spesies meyalo tingkat bahaya. Dila boleh menentukan ula berbisa hanya berdasarkan label otomatis. Simpan gambar asli ode pemeriksaan lo ahli.",
    "red_junglefowl": "Manu hutan merah botiya manu u monga to buta wawu biasa yilumulo to tepi huta. Tiyombu leluhur liar lo ayam domestik. To tampa u dekat permukiman, gambar paralu diperiksa ode membedakan manu hutan wolo ayam domestik meyalo hibrida.",
    "philippine_megapode": "Manu gosong Filipina botiya manu u banyak yilumulo to buta. Telur liyo dierami wolo panas lo bahan organik u membusuk meyalo buta u hangato, dila selalu dierami induk. Kamera to buta mowali merekam aktivitas monga wawu pergerakan dekat sarang.",
    "sulawesi_ground_dove": "Delimukan Sulawesi botiya manu merpati endemik u banyak berjalan wawu monga to lantai huta. Tiyombu susah odelo langsung, jadi kamera jebak to jalur berguna ode mencatat keberadaan wawu aktivitas liyo.",
    "human": "Deteksi tawu mowali motunggulo kunjungan lo tim lapangan meyalo aktivitas uwewo to delomo kamera. Akses paralu dibatasi sababu gambar mowali woluwo data pribadi. Taati aturan persetujuan, lama penyimpanan, wawu privasi proyek bohuliyo gambar ditampilkan meyalo dibagikan.",
    "domestic_cat": "Kucing domestik mowali masuk ode tepi huta lonto permukiman meyalo pos lapangan. Deteksi liyo paralu dicatat sababu kucing u bebas berkeliaran mowali berinteraksi wolo satwa liar wawu motunggulo pengaruh lo tawu to delomo lokasi.",
    "gagang_bayam": "Manu gagang-bayam botiya manu taluhu wolo pale u hayambo. Tiyombu monga to lahan basah dangkal, lumpur, wawu tampa tergenang. Hasil deteksi mowali motunggulo kondisi taluhu wawu ketersediaan tampa monga u dangkal wawu terbuka.",
    "kuntul": "Kelas botiya mencakup manu kuntul moputi u monga to delomo taluhu, padang rumput, meyalo dekat ternak. Warna bulu, paruh, pale, ukuran, wawu habitat paralu diperiksa manual sababu beberapa spesies kuntul odelo sama to gambar kamera.",
}

HUMAN_FALLBACK_PHOTO = {
    "url": "https://inaturalist-open-data.s3.amazonaws.com/photos/2641761/medium.jpg",
    "attribution": "© Greg Lasley",
    "license": "CC BY-NC 4.0",
    "source": "https://www.inaturalist.org/photos/2641761",
}

st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(180deg, #f6faf6 0%, #eef4ef 100%);}
    .block-container {padding-top: 1.6rem; max-width: 1500px;}
    .hero {background: linear-gradient(115deg,#153e2e,#286447);color:#fff;padding:1.45rem 1.7rem;border-radius:18px;margin-bottom:1rem;box-shadow:0 12px 30px rgba(18,65,43,.18)}
    .hero h1 {margin:0;font-size:2.05rem}.hero p{margin:.35rem 0 0;color:#dcebe1}
    .status {color:white;padding:1rem 1.3rem;border-radius:14px;margin:.25rem 0 1rem;box-shadow:0 7px 20px rgba(0,0,0,.12)}
    .status h2{margin:.1rem 0;font-size:1.7rem}.status p{margin:0;opacity:.9;font-weight:700;letter-spacing:.08em}
    .danger{background:linear-gradient(110deg,#981f2a,#d84949)}.warning{background:linear-gradient(110deg,#a65b00,#e89b28)}
    .receiving{background:linear-gradient(110deg,#155aa8,#3186ce)}.safe{background:linear-gradient(110deg,#1c6539,#3c9157)}
    .wild-card {border:1px solid #dbe6dc;border-radius:14px;padding:1rem;background:white;min-height:215px}
    .small-muted{font-size:.82rem;color:#66756a}.footer{text-align:center;color:#647168;padding:2rem 0 .5rem;font-size:.86rem}
    </style>
    """,
    unsafe_allow_html=True,
)


def t(key: str) -> str:
    return UI[st.session_state.get("language", "en")].get(key, key)


def read_feed(path: Path) -> dict[str, Any]:
    """Read around an atomic writer; a partial JSON write becomes an empty feed."""
    if not path.exists():
        return {}
    for _ in range(2):
        try:
            with path.open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def image_bytes(path: str | Path) -> bytes | None:
    try:
        candidate = Path(path)
        if candidate.is_file():
            payload = candidate.read_bytes()
            return payload if len(payload) > 400 else None
    except OSError:
        pass
    return None


def parse_confidence(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            number = float(value.strip().replace("%", ""))
            return number / 100 if number > 1 else number
        number = float(value)
        return number / 100 if number > 1 else number
    except (TypeError, ValueError):
        return None


def format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "—"
    if seconds < 60:
        return f"{seconds:.0f} s"
    minutes, sec = divmod(int(seconds), 60)
    return f"{minutes}m {sec:02d}s"


def packet_frame(raw: Any) -> pd.DataFrame:
    if not isinstance(raw, list) or not raw:
        return pd.DataFrame(columns=["packet", "time_elapsed"])
    frame = pd.DataFrame(raw)
    if not {"packet", "time_elapsed"}.issubset(frame.columns):
        return pd.DataFrame(columns=["packet", "time_elapsed"])
    frame["packet"] = pd.to_numeric(frame["packet"], errors="coerce")
    frame["time_elapsed"] = pd.to_numeric(frame["time_elapsed"], errors="coerce")
    return frame.dropna(subset=["packet", "time_elapsed"]).sort_values("packet")


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def representative_photo(taxon: str) -> dict[str, str] | None:
    """Fetch iNaturalist's default taxon photo and retain attribution."""
    if not taxon:
        return None
    try:
        response = requests.get(
            "https://api.inaturalist.org/v1/taxa",
            params={"q": taxon, "per_page": 5},
            timeout=5,
            headers={"User-Agent": "GreenEdgeTelemetryDashboard/1.0"},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        wanted = taxon.casefold()
        item = next(
            (r for r in results if str(r.get("name", "")).casefold() == wanted),
            results[0] if results else None,
        )
        photo = (item or {}).get("default_photo") or {}
        url = photo.get("medium_url") or photo.get("square_url")
        if not url:
            return None
        return {
            "url": url.replace("square", "medium"),
            "attribution": photo.get("attribution", "iNaturalist contributor"),
            "license": photo.get("license_code") or "see source",
            "source": f"https://www.inaturalist.org/taxa/{item.get('id')}",
        }
    except (requests.RequestException, ValueError, TypeError):
        return None


def local_wildlife_image(class_id: str) -> Path | None:
    for suffix in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = LOCAL_WILDLIFE_FOLDER / f"{class_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def normalize_history(raw: Any) -> pd.DataFrame:
    columns = ["timestamp", "target", "confidence", "type"]
    if not isinstance(raw, list) or not raw:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(raw)
    for col in columns:
        if col not in frame:
            frame[col] = ""
    frame = frame[columns].copy()
    frame["target"] = frame["target"].fillna("unknown").astype(str).str.strip()
    return frame


with st.sidebar:
    language_name = st.selectbox(t("language"), list(LANGUAGES), index=0)
    st.session_state["language"] = LANGUAGES[language_name]
    refresh_seconds = st.select_slider(t("refresh"), options=[2, 5, 10, 30], value=5, format_func=lambda x: f"{x}s")
    if st.session_state["language"] == "gor":
        st.caption("⚠️ " + t("localization_note"))
    st.markdown("---")
    st.caption(f"Feed: `{FEED_FILE}`")
    st.caption(f"Images: `{IMAGE_FOLDER}`")

try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=refresh_seconds * 1000, key="green_edge_refresh")
except ImportError:
    st.sidebar.button("↻ Refresh")

data = read_feed(FEED_FILE)
target = str(data.get("target", "Standby Status")).strip()
confidence_raw = data.get("confidence", "0%")
confidence_num = parse_confidence(confidence_raw)
confidence_text = f"{confidence_num:.1%}" if confidence_num is not None else str(confidence_raw)
event_type = str(data.get("type", "Idle"))
chunks_received = max(0, int(data.get("chunks_received", 0) or 0))
total_chunks = max(1, int(data.get("total_chunks", 1) or 1))
progress = min(1.0, chunks_received / total_chunks)
history_df = normalize_history(data.get("history", []))
packets_df = packet_frame(data.get("packet_timestamps", []))

feed_age = None
if FEED_FILE.exists():
    feed_age = max(0.0, datetime.now(timezone.utc).timestamp() - FEED_FILE.stat().st_mtime)
receiver_status = t("online") if feed_age is not None and feed_age <= 15 else t("delayed") if feed_age is not None and feed_age <= 60 else t("offline")
receiver_icon = "🟢" if feed_age is not None and feed_age <= 15 else "🟠" if feed_age is not None and feed_age <= 60 else "🔴"

st.markdown(
    f"<div class='hero'><h1>🌿 {t('title')}</h1><p>{t('subtitle')}</p></div>",
    unsafe_allow_html=True,
)

lower_type = event_type.casefold()
if "primary" in lower_type:
    status_class, status_line, status_title = "danger", t("active"), f"🚨 {target.replace('_', ' ').upper()} · {confidence_text}"
elif "background" in lower_type:
    status_class, status_line, status_title = "warning", t("background"), f"🔎 {target.replace('_', ' ').upper()} · {confidence_text}"
elif 0 < chunks_received < total_chunks:
    status_class, status_line, status_title = "receiving", t("receiving"), f"📡 {chunks_received}/{total_chunks}"
else:
    status_class, status_line, status_title = "safe", t("secure"), t("monitoring")

st.markdown(
    f"<div class='status {status_class}'><p>{status_line}</p><h2>{status_title}</h2></div>",
    unsafe_allow_html=True,
)

tab_live, tab_events, tab_guide, tab_system = st.tabs([f"📡 {t('live')}", f"📊 {t('events')}", f"🦉 {t('guide')}", f"🧰 {t('system')}"])

with tab_live:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("packets"), f"{chunks_received} / {total_chunks}")
    m2.metric(t("progress"), f"{progress:.1%}")
    m3.metric(t("confidence"), confidence_text)
    m4.metric(t("last_update"), f"{receiver_icon} {receiver_status}")
    st.progress(progress)

    left, right = st.columns([1, 1.15])
    with left:
        st.subheader(f"📈 {t('latency')}")
        if len(packets_df) > 1:
            st.line_chart(packets_df, x="packet", y="time_elapsed", x_label="Chunk", y_label="Elapsed time (s)")
        else:
            st.info(t("no_packets"))
    with right:
        st.subheader(f"🖼️ {t('canvas')}")
        last_archived = str(data.get("last_archived_image", ""))
        if 0 < chunks_received < total_chunks and image_bytes(LIVE_IMAGE):
            st.image(image_bytes(LIVE_IMAGE), caption=f"📥 {t('reconstructing')} ({chunks_received}/{total_chunks})", use_container_width=True)
        elif last_archived and image_bytes(last_archived):
            st.image(image_bytes(last_archived), caption=f"✅ {t('snapshot')}: {target.replace('_', ' ')}", use_container_width=True)
        elif image_bytes(LIVE_IMAGE):
            st.image(image_bytes(LIVE_IMAGE), caption=t("canvas"), use_container_width=True)
        else:
            st.info(t("waiting"))

with tab_events:
    e1, e2, e3 = st.columns(3)
    e1.metric(t("event_total"), len(history_df))
    if not history_df.empty:
        counts = history_df["target"].str.replace("_", " ").str.title().value_counts()
        e2.metric(t("top_class"), counts.index[0])
        e3.metric(t("source"), str(history_df.iloc[-1]["type"]) or "—")
    else:
        e2.metric(t("top_class"), "—")
        e3.metric(t("source"), "—")

    chart_col, log_col = st.columns([0.9, 1.1])
    with chart_col:
        st.subheader(t("distribution"))
        if not history_df.empty:
            chart_data = history_df["target"].str.replace("_", " ").str.title().value_counts().rename_axis("Class").reset_index(name="Events")
            try:
                import plotly.express as px

                figure = px.bar(chart_data, x="Events", y="Class", orientation="h", color="Events", color_continuous_scale="Greens")
                figure.update_layout(height=max(330, len(chart_data) * 30), margin=dict(t=10, b=10, l=10, r=10), coloraxis_showscale=False)
                st.plotly_chart(figure, use_container_width=True)
            except ImportError:
                st.bar_chart(chart_data, x="Class", y="Events")
        else:
            st.info(t("no_history"))
    with log_col:
        st.subheader(t("records"))
        if not history_df.empty:
            classes = sorted(history_df["target"].dropna().unique())
            selected = st.multiselect(t("category"), classes, default=classes)
            visible = history_df[history_df["target"].isin(selected)].iloc[::-1]
            st.dataframe(visible, use_container_width=True, hide_index=True)
            st.download_button(t("download"), visible.to_csv(index=False).encode("utf-8"), "green_edge_events.csv", "text/csv")
        else:
            st.info(t("no_history"))

    st.subheader(f"📚 {t('gallery')}")
    archive = sorted(glob.glob(str(IMAGE_FOLDER / "reconstructed_*.jpg")), key=os.path.getmtime, reverse=True)
    if archive:
        gallery_cols = st.columns(4)
        for index, path in enumerate(archive[:40]):
            filename = Path(path).stem
            match = re.match(r"reconstructed_([^_]+)_([^_]+)_(.+)", filename)
            label = match.group(3).replace("_", " ").upper() if match else filename.replace("_", " ")
            stamp = f"{match.group(1)} {match.group(2)}" if match else ""
            payload = image_bytes(path)
            if payload:
                with gallery_cols[index % 4]:
                    st.image(payload, caption=f"🏷️ {label}\n{stamp}", use_container_width=True)
    else:
        st.info(t("no_archive"))

with tab_guide:
    search_col, category_col = st.columns([2, 1])
    query = search_col.text_input(t("search"), placeholder="maleo / anoa / tarsier …").casefold().strip()
    category_options = ["all", *CATEGORIES]
    selected_category = category_col.selectbox(t("category"), category_options, format_func=lambda x: t("all") if x == "all" else CATEGORIES[x][st.session_state["language"]])
    filtered = [
        animal for animal in WILDLIFE
        if (selected_category == "all" or animal["category"] == selected_category)
        and (not query or query in " ".join([animal["id"], animal["en"], animal["id_name"], animal["scientific"]]).casefold())
    ]
    cards = st.columns(3)
    for index, animal in enumerate(filtered):
        language = st.session_state["language"]
        common_name = (
            animal["en"] if language == "en"
            else GOR_NAMES.get(animal["id"], animal["id_name"]) if language == "gor"
            else animal["id_name"]
        )
        description = (
            animal["en_desc"] if language == "en"
            else GOR_DESC.get(animal["id"], animal["id_desc"]) if language == "gor"
            else animal["id_desc"]
        )
        with cards[index % 3]:
            st.markdown(f"### {common_name}")
            st.caption(f"*{animal['scientific']}* · `{animal['id']}`")
            local_photo = local_wildlife_image(animal["id"])
            photo = (
                HUMAN_FALLBACK_PHOTO if animal["id"] == "human"
                else representative_photo(animal["taxon"])
            ) if local_photo is None else None
            if local_photo:
                st.image(str(local_photo), caption=t("representative"), use_container_width=True)
            elif photo:
                st.image(photo["url"], caption=t("representative"), use_container_width=True)
                st.caption(f"Photo: {photo['attribution']} · {photo['license']} · [iNaturalist]({photo['source']})")
            else:
                st.info(t("photo_unavailable"))
            st.write(description)
            st.caption(t("image_note"))

with tab_system:
    rate = None
    eta = None
    if len(packets_df) > 1:
        elapsed = float(packets_df["time_elapsed"].iloc[-1] - packets_df["time_elapsed"].iloc[0])
        received_span = float(packets_df["packet"].iloc[-1] - packets_df["packet"].iloc[0])
        if elapsed > 0 and received_span > 0:
            rate = received_span / elapsed
            eta = max(0, total_chunks - chunks_received) / rate
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(t("feed_age"), format_duration(feed_age))
    s2.metric(t("throughput"), f"{rate:.2f} chunks/s" if rate else "—")
    s3.metric(t("eta"), format_duration(eta))
    s4.metric("JSON", "Valid" if data else "Missing / invalid")
    st.json({
        "feed_file": str(FEED_FILE),
        "image_folder": str(IMAGE_FOLDER),
        "last_archived_image": data.get("last_archived_image"),
        "event_type": event_type,
        "active_classes": len(WILDLIFE),
        "auto_refresh_seconds": refresh_seconds,
    })

st.markdown(
    f"<div class='footer'>© {datetime.now().year} Green Edge Project · Developed by Muhammad Bondan Vitto Ramadhan · {t('footer')}<br>Wildlife photographs remain subject to their credited source licences.</div>",
    unsafe_allow_html=True,
)
