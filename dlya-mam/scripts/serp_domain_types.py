"""Тип домена в выдаче. Разметка моя, по названию и заголовкам; это ЗАМЕР, не слепой.

Типы:
  clinic     — частная клиника или сеть (статьи-блоги клиник тоже сюда)
  state      — государственные медучреждения, профобщества, НМИЦ, вузы, порталы Минздрава
  media      — медицинские справочники и медиа без своей клиники (энциклопедии, журналы, СМИ)
  brand      — производители: смеси, подгузники, лекарства, техника
  lab        — лаборатории
  shop       — аптеки, маркетплейсы, книжные
  aggregator — карты, каталоги врачей и клиник
  telemed    — онлайн-консультации врачей
  course     — школы, курсы, авторские блоги-продажи (консультанты, педиатры-блогеры)
  social     — видео, соцсети, мессенджеры, Дзен
  yandex     — сервисы и самореклама Яндекса (видео Яндекса, Алиса, Директ)
  other      — остальное
"""

EXPLICIT = {
    # state / профобщества / наука
    "pediatr-russia.ru": "state", "nczd.ru": "state", "fnkc-fmba.ru": "state", "profilaktica.ru": "state",
    "org.gnicpm.ru": "state", "rgnkc.ru": "state", "mos.ru": "state", "mosgorzdrav.ru": "state", "sp62.mos.ru": "state",
    "gu99.site.gov.spb.ru": "state", "dgb.spb.ru": "state", "msch9fmba.ru": "state", "mmccdzm.ru": "state",
    "dzunmmc.gosuslugi.ru": "state", "med-b-kamenskaya-r22.gosweb.gosuslugi.ru": "state", "bsmu.by": "state",
    "raaci.ru": "state", "rcrm.by": "state", "nkcgv.ncagp.ru": "state", "kcozsrnsk.ru": "state",
    "cyberleninka.ru": "state", "rsmu.ru": "state", "base.garant.ru": "state", "dgkb8-chel.ru": "state",
    "cheldgp4.ru": "state", "dgp174.ru": "state", "kst27.ru": "state", "privivka.spb.ru": "state",
    "здоровыедети124.рф": "state", "gosgv.ru": "course",
    # media / справочники
    "probolezny.ru": "media", "krasotaimedicina.ru": "media", "nsk.krasotaimedicina.ru": "media", "doct.ru": "media",
    "msdmanuals.com": "media", "vidal.ru": "media", "rlsnet.ru": "media", "diseases.medelement.com": "media",
    "lvrach.ru": "media", "medaboutme.ru": "media", "t-j.ru": "media", "family.rambler.ru": "media",
    "championat.com": "media", "lenta.ru": "media", "ntv.ru": "media", "tv3.ru": "media", "belta.by": "media",
    "ru.wikipedia.org": "media", "руни.рф": "media", "ru.ruwiki.ru": "media", "rmj.ru": "media", "pharmateca.ru": "media",
    "akev.info": "media", "med-click.ru": "media", "ya-roditel.ru": "media", "medeste.ru": "media",
    "lit-baby.ru": "media", "uroki4mam.ru": "media", "zn48.ru": "media", "immunitet.ru": "media", "vse-privivki.ru": "media",
    "medicina.ru": "clinic", "smdoctor.ru": "clinic", "fdoctor.ru": "clinic", "docdeti.ru": "clinic",
    # brand
    "nestlebaby.ru": "brand", "nutriclub.ru": "brand", "nutrilak.com": "brand", "huggies.ru": "brand", "femibion.ru": "brand",
    "frutonyanya.ru": "brand", "nurofen.ru": "brand", "rengalin.ru": "brand", "philips.ru": "brand", "kabrita.ru": "brand",
    "similac.ru": "brand", "enterosgel.ru": "brand", "nuvita-baby.ru": "brand", "medela.ru": "brand", "bepanthen.ru": "brand",
    "antigrippin-np.ru": "brand", "bronchipret.com": "brand", "licopid.ru": "brand", "suprastinex.ru": "brand",
    "aquadetrim.com": "brand", "kreon.ru": "brand", "colicrocodile.ru": "brand", "oscillo.ru": "brand", "rinza.ru": "brand",
    "rafamin.ru": "brand", "normobact.ru": "brand", "bobotik.ru": "brand", "imodium.ru": "brand", "dinobutin.ru": "brand",
    "microlax.ru": "brand", "duphalac.ru": "brand", "nizhpharm.ru": "brand", "kamistad.ru": "brand", "derinat.ru": "brand",
    "anaferon.ru": "brand", "akriderm.com": "brand", "naos.ru": "brand", "aravia.ru": "brand", "geltek.ru": "brand",
    "nasivin.ru": "brand", "nasivinkids.ru": "brand", "irs19.ru": "brand", "comfoderm.ru": "brand", "lipobase.ru": "brand",
    "dantinorm.ru": "brand", "mamako.ru": "brand", "edkarik.ru": "brand", "milkrb.ru": "brand", "agulife.ru": "brand",
    "maslo-dishi.ru": "brand", "biorise.ru": "brand", "celt.ru": "brand", "cetrine.ru": "brand", "imma.ru": "brand",
    "immuc.ru": "brand", "pro-tektika.ru": "brand", "elfea.ru": "brand", "erdamed.ru": "brand", "sundelight.by": "brand",
    "chh.ru": "brand", "snup.ru": "brand", "kormybaby.ru": "brand", "boobl-goom.ru": "brand", "stellanin.pro": "brand",
    # lab
    "gemotest.ru": "lab", "invitro.ru": "lab", "citilab.ru": "lab", "labquest.ru": "lab", "gemabank.ru": "lab",
    "chromolab.ru": "lab", "cmed72.ru": "lab", "kdc5.com": "lab",
    # shop
    "megapteka.ru": "shop", "apteka.ru": "shop", "eapteka.ru": "shop", "stolichki.ru": "shop", "zdravcity.ru": "shop",
    "zdorov.ru": "shop", "superapteka.ru": "shop", "rigla.ru": "shop", "polza.ru": "shop", "rostov-na-donu.asna.ru": "shop",
    "spb.asna.ru": "shop", "uteka.ru": "shop", "nn.uteka.ru": "shop", "apteka.magnit.ru": "shop", "ozerki.ru": "shop",
    "gorzdrav.org": "shop", "avito.ru": "shop", "ozon.ru": "shop", "labirint.ru": "shop", "chitai-gorod.ru": "shop",
    "litres.ru": "shop", "livelib.ru": "shop", "books.yandex.ru": "shop", "budzdorov.ru": "shop", "paracels.net": "shop",
    "orteka.ru": "shop",
    # aggregator
    "2gis.ru": "aggregator", "zoon.ru": "aggregator", "prodoctorov.ru": "aggregator", "napopravku.ru": "aggregator",
    "nsk.docdoc.ru": "aggregator", "sberhealth.ru": "aggregator", "lk.sberhealth.ru": "aggregator",
    "uslugi.yandex.ru": "aggregator", "yamed.ru": "aggregator", "openclinics.ru": "aggregator", "bestclinic.ru": "aggregator",
    "c9m.ru": "aggregator",
    # telemed
    "doctu.ru": "telemed", "teledoctor24.ru": "telemed", "doctorvika.ru": "telemed", "doctis.ru": "telemed",
    "bibicall.ru": "telemed", "sprosivracha.com": "telemed", "health.genotek.ru": "telemed", "docma.ru": "telemed",
    # course / авторские
    "vitanova-university.ru": "course", "mamababy.academy": "course", "mamababy-spb.ru": "course",
    "shkolamaterinstva.ru": "course", "smiles-academy.ru": "course", "skillforskin.ru": "course", "ecodpo.ru": "course",
    "learntomama.ru": "course", "kulturaprikorma.ru": "course", "pricorm.ru": "course", "progv.ru": "course",
    "insidemama.ru": "course", "insidemama.online": "course", "eshmalysh.ru": "course", "кормимдеток.рф": "course",
    "legkie-rody.ru": "course", "glavmama.ru": "course", "baby-sleep.ru": "course", "sonmalysha.ru": "course",
    "milkyfairies.ru": "course", "doulann.ru": "course", "novokrinitskii.com": "course", "agapovmd.ru": "course",
    "pediatrkravtsova.pro": "course", "doc-erofeeva.ru": "course", "doctorderm.su": "course", "sozvezdie.center": "course",
    "elena-materinstvo.ru": "course", "lunora.mom": "course", "gc.new-degree.ru": "course", "prinyatie.com": "course",
    "shok.online": "course", "nanny-mamemozhno.ru": "course", "parents-web.foxford.ru": "course", "gv-vrn.ru": "course",
    "pravonachudo.ru": "course", "anosc.ru": "course",
    # social
    "youtube.com": "social", "vk.ru": "social", "vkvideo.ru": "social", "rutube.ru": "social", "tiktok.com": "social",
    "t.me": "social", "telegram.me": "social", "dzen.ru": "social", "music.yandex.ru": "social", "music.apple.com": "social",
    "zvuk.com": "social", "music.mts.ru": "social", "shazam.com": "social", "yandex.ru": "yandex",
    # yandex self-promo in ads
    "cowork.bitrix24.ru": "other", "leads.su": "other", "mrqz.me": "other", "meetup.bitrix24.events": "other",
    "sberbusiness.live": "other", "yes-towers.ru": "other", "go.moy-test24.ru": "other", "sochno-krd.ru": "other",
    "crazybeach.ru": "other", "lavka.yandex.ru": "other", "yookassa.ru": "other", "sosnovy-bor.eltex.ru": "other",
    "ivf.uz": "clinic",
}
EXPLICIT.update({
    "calorai.io": "other", "baby-two-teeth.clients.site": "clinic", "happybaby.ru": "shop", "detmir.ru": "shop",
    "wildberries.ru": "shop", "mam-shop.ru": "shop", "mimakids.com.ru": "shop", "gipopo-baby.ru": "shop",
    "vitamax-russia.shop": "shop", "мамкози.рф": "shop", "go.ast.ru": "shop", "cytamins.ru": "brand", "ismigen.ru": "brand",
    "lasolvan.ru": "brand", "levomecole.ru": "brand", "maxicold.ru": "brand", "otipax.ru": "brand", "stormoff.ru": "brand",
    "urteks.ru": "brand", "arosha.com.ru": "brand", "dobryanka-rus.ru": "brand", "вирусамнет.рф": "brand",
    "krapivnica.info": "brand", "kartazhizni.ru": "lab", "preventera.pro": "other", "alice.yandex.ru": "yandex",
    "apertosib.ru": "clinic", "santal-nsk.ru": "clinic", "медцентр54.рф": "clinic", "profi.ru": "aggregator",
    "practicum.yandex.ru": "other", "maps-edu.ru": "course", "lp-edpro1.ru": "course", "pitanws90.tutorplace.ru": "course",
    "sleepbabyandmom.online": "course", "vforme.pro": "course", "croopa.ru": "course", "u4is-segodnya.ru": "course",
    "rakshejkimatki.ru": "other", "rc-ortos.ru": "clinic", "mpi-msk.ru": "course", "svetlana-sochi.ru": "other",
    "ms-stomheihe.ru": "clinic", "imomy.ru": "course",
})

LOCAL = {
    "novosibirsk.mamadeti.ru", "nsk.docdoc.ru", "nsk.krasotaimedicina.ru", "vz-nsk.ru", "euromednsk.ru", "avicenna-nsk.ru",
    "novosibirsk.yarkiedeti.ru", "kcozsrnsk.ru", "loriya.ru", "cnmt.ru", "santal-nsk.ru", "медцентр54.рф",
    "skydent.ru", "styledent.ru", "apertosib.ru", "avanta-med.ru", "mama-lab.ru",
}

CLINIC_HINTS = ("clinic", "klinik", "mc", "med", "dent", "zub", "ctoma", "smile", "hospital", "lor", "polyclin",
                "deti", "mamadeti", "fomin", "sovamed", "medsi", "sanitas", "zdravitsa", "renewal", "centr", "center",
                "allergo", "reacentr", "doctor", "euro", "s0.", "1dmc", "kliomed", "nv-", "ogni", "kdpmc", "alfazdrav",
                "budzdorov", "kapelnica", "virilis", "elena", "azelik", "omnitus", "bleskmed", "integramed", "insan",
                "meddynasty", "duet", "smitra", "rekamedika", "impuls", "newmed", "edkarik", "major", "doctor03",
                "rostochek", "yarkiedeti", "vz-nsk", "avicenna", "cnmt", "loriya", "ihc", "vitaclinica", "premium",
                "expert", "arvis", "ugmk", "nikid", "lahta", "eastclinic", "tz.clinic", "gmsclinic", "emcmos", "pregnancy",
                "topsmile", "dinastiya", "klinikaperceva", "irs", "prbmo", "kit-", "zs-mc", "mama-lab", "eurodon",
                "cfm.ru", "ramsay", "lit-clinic", "ihospital", "sun-clinic", "institut", "medgorod", "fantasy", "budz")


def domain_type(d):
    if d in EXPLICIT:
        return EXPLICIT[d]
    if any(h in d for h in CLINIC_HINTS):
        return "clinic"
    return "other"


def is_local(d, url=""):
    return int(d in LOCAL or "nsk" in d or "novosib" in d or "54" in d or "/novosibirsk" in url or "nsk." in url)
