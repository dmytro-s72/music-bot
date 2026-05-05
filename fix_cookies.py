import os

# Твої куки. Навіть якщо тут пробіли, скрипт це справить.
RAW_DATA = """
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

def generate_valid_cookies():
    file_path = 'cookies.txt'
    with open(file_path, 'w', encoding='utf-8') as f:
        # Заголовок формату Netscape
        f.write("# Netscape HTTP Cookie File\n\n")
        
        for line in RAW_DATA.strip().split('\n'):
            # Розбиваємо рядок по будь-яким пробілам
            columns = line.split()
            if len(columns) >= 7:
                # З'єднуємо перші 6 частин табуляцією, а останню (значення) додаємо в кінці
                fixed_line = "\t".join(columns[:6]) + "\t" + " ".join(columns[6:])
                f.write(fixed_line + "\n")

if __name__ == "__main__":
    generate_valid_cookies()
    print("✅ cookies.txt створено з правильними табуляціями!")
