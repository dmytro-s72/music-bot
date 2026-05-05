import os

# Твої куки, скопійовані з логів. 
# Скрипт сам перетворить пробіли на потрібні табуляції.
RAW_COOKIES = """
.youtube.com FALSE / TRUE 1810919112.19605 __Secure-1PAPISID lFlk-pCBHHSgqVR0/Al2ptOFjuHt2NEnr_
.youtube.com FALSE / TRUE 1809501688.274655 __Secure-1PSIDTS sidts-CjQBhkeRd2OZFf84DZiVTvdcXs0Nq1Zil2LTMudfMZbXxAnENpfxN_PSk204LEvEWN9Aqqu0EAA
.youtube.com FALSE / TRUE 1810919112.196821 __Secure-3PSID g.a0008wiMDGUfaXN9c6LDAP94GgR_16CBZb3TjsBbiKZ8KHpcMMaRVSi7q5VRp3bZG-WaZFm2BQACgYKAWsSARASFQHGX2MiCUvGBXDIvEitIJBdFh7hYRoVAUF8yKrbJYDN5AoObxu0neOCPyfr0076
.youtube.com FALSE / TRUE 1809501688.27502 __Secure-3PSIDTS sidts-CjQBhkeRd2OZFf84DZiVTvdcXs0Nq1Zil2LTMudfMZbXxAnENpfxN_PSk204LEvEWN9Aqqu0EAA
.youtube.com FALSE / TRUE 1791177554.133529 __Secure-BUCKET CLcG
.youtube.com FALSE / FALSE 1810919112.195777 APISID HbLvXOy8m2eUzSBw/AZBoMhl-52J43qfWI
.youtube.com FALSE / TRUE 1808311468.693482 LOGIN_INFO AFmmF2swRgIhAKdqcEcRHjvP8dLV-yHAVYYkMtMQnQ3o0H6--WJb0mhdAiEAq2wGOKlrJlIDAN0EyX9uGDHkQMMXzHdfGnL7whEA7oI:QUQ3MjNmenFiQnRoTHF1dVJ5TW5EUVJpNlJZQkdSYS1MbnpHWVFrN05HYVBCWmRKR1ZWdXc1eEd3Wmh1YXZIWnhIVm1jTGk4MXN0Ujhja3lteUE5LTZ0VDNqZlF5dG9RSzlubG5TZlFvOFE3TkNlRWctOEdINFFWRHFIM3MyaUFXVTVfMUZPYWpHNU55eHdTVlEtN1dpREE3UVFuUnFQNVRB
.youtube.com FALSE / FALSE 1810919112.196624 SID g.a0008wiMDGUfaXN9c6LDAP94GgR_16CBZb3TjsBbiKZ8KHpcMMaRWPPZaFEwV9z4HNAONGy3fAACgYKAacSARASFQHGX2MiC0Y9HJ8gu-xJxMeLEzTbthoVAUF8yKqTkKVCpBoDHFKCQ-DNObOf0076
.youtube.com FALSE / FALSE 1809501688.275223 SIDCC AKEyXzXhR_Aw1PP4Qgc_AdWKiq4ewVyzBSvHiUphrfeiUuNPGRNCoQUBlkdCNFQHUplEpr1Jpw
.youtube.com FALSE / TRUE 1793515711.535062 VISITOR_INFO1_LIVE P8f2iYwVWI0
"""

def save_fixed_cookies():
    with open('cookies.txt', 'w', encoding='utf-8') as f:
        # Додаємо стандартний заголовок Netscape
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n\n")
        
        for line in RAW_COOKIES.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Розбиваємо рядок по пробілах
            parts = line.split()
            
            # Якщо частин >= 7, з'єднуємо перші 6 табуляцією, а залишок (значення) - як є
            if len(parts) >= 7:
                # domain, flag, path, secure, expiration, name, value
                new_line = "\t".join(parts[:6]) + "\t" + " ".join(parts[6:])
                f.write(new_line + "\n")
            elif len(parts) == 6:
                # На випадок, якщо значення порожнє
                f.write("\t".join(parts) + "\t\n")

if __name__ == "__main__":
    save_fixed_cookies()
    print("✅ Файл cookies.txt успішно згенеровано з правильними табуляціями!")
