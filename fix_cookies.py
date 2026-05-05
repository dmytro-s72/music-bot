import os

# Текст твоїх куків прямо в скрипті (це найнадійніший спосіб)
raw_cookies = """
.youtube.com	FALSE	/	TRUE	1810919112.19605	__Secure-1PAPISID	lFlk-pCBHHSgqVR0/Al2ptOFjuHt2NEnr_
.youtube.com	FALSE	/	TRUE	1810919112.196725	__Secure-1PSID	g.a0008wiMDGUfaXN9c6LDAP94GgR_16CBZb3TjsBbiKZ8KHpcMMaRMZvSHMwpUSlkGP7I3CTcXgACgYKAcYSARASFQHGX2MiV3EAZW_Kx6VUBi2fcB7P7RoVAUF8yKqp2adaPFIV3-mC5duw0_Xj0076
.youtube.com	FALSE	/	TRUE	1809501688.275413	__Secure-1PSIDCC	AKEyXzWPXKZY7NXHOV9xy3QhoIdFhn-MxGIbUfBQ_j7vWF5mpnW6hRaQNWLPN5nCKVSUNBoXkcM
.youtube.com	FALSE	/	TRUE	1810919112.196136	__Secure-3PAPISID	lFlk-pCBHHSgqVR0/Al2ptOFjuHt2NEnr_
.youtube.com	FALSE	/	TRUE	1810919112.196821	__Secure-3PSID	g.a0008wiMDGUfaXN9c6LDAP94GgR_16CBZb3TjsBbiKZ8KHpcMMaRVSi7q5VRp3bZG-WaZFm2BQACgYKAWsSARASFQHGX2MiCUvGBXDIvEitIJBdFh7hYRoVAUF8yKrbJYDN5AoObxu0neOCPyfr0076
.youtube.com	FALSE	/	TRUE	1809501688.275591	__Secure-3PSIDCC	AKEyXzW4-8OXHwB4zgyPdoOwXZIGf48OddVNmg6lqzBQJBm_AXuAgWNktKp-gwHhcycMxK9aEg
.youtube.com	FALSE	/	FALSE	1810919112.195777	APISID	HbLvXOy8m2eUzSBw/AZBoMhl-52J43qfWI
.youtube.com	FALSE	/	FALSE	1810919112.195353	HSID	ADzdV_XTR06ZkWxfI
.youtube.com	FALSE	/	TRUE	1808311468.693482	LOGIN_INFO	AFmmF2swRgIhAKdqcEcRHjvP8dLV-yHAVYYkMtMQnQ3o0H6--WJb0mhdAiEAq2wGOKlrJlIDAN0EyX9uGDHkQMMXzHdfGnL7whEA7oI:QUQ3MjNmenFiQnRoTHF1dVJ5TW5EUVJpNlJZQkdSYS1MbnpHWVFrN05HYVBCWmRKR1ZWdXc1eEd3Wmh1YXZIWnhIVm1jTGk4MXN0Ujhja3lteUE5LTZ0VDNqZlF5dG9RSzlubG5TZlFvOFE3TkNlRWctOEdINFFWRHFIM3MyaUFXVTVfMUZPYWpHNU55eHdTVlEtN1dpREE3UVFuUnFQNVRB
.youtube.com	FALSE	/	TRUE	1812525758.338885	PREF	f4=4000000&f6=40000000&tz=Europe.Kiev&f5=30000&f7=150&repeat=NONE&gl=US
.youtube.com	FALSE	/	TRUE	1810919112.195955	SAPISID	lFlk-pCBHHSgqVR0/Al2ptOFjuHt2NEnr_
.youtube.com	FALSE	/	FALSE	1810919112.196624	SID	g.a0008wiMDGUfaXN9c6LDAP94GgR_16CBZb3TjsBbiKZ8KHpcMMaRWPPZaFEwV9z4HNAONGy3fAACgYKAacSARASFQHGX2MiC0Y9HJ8gu-xJxMeLEzTbthoVAUF8yKqTkKVCpBoDHFKCQ-DNObOf0076
.youtube.com	FALSE	/	FALSE	1809501688.275223	SIDCC	AKEyXzXhR_Aw1PP4Qgc_AdWKiq4ewVyzBSvHiUphrfeiUuNPGRNCoQUBlkdCNFQHUplEpr1Jpw
.youtube.com	FALSE	/	TRUE	1810919112.195619	SSID	A_ciKxR_dMkv5c_d1
.youtube.com	FALSE	/	TRUE	1793515711.535062	VISITOR_INFO1_LIVE	P8f2iYwVWI0
.youtube.com	FALSE	/	TRUE	1793515711.535414	VISITOR_PRIVACY_METADATA	CgJVQRIEGgAgag%3D%3D
.youtube.com	FALSE	/	FALSE	wide	0
.youtube.com	FALSE	/	TRUE	YSC	jSFE7x7Ctuc
"""

def save_fixed_cookies():
    cookie_file = 'cookies.txt'
    with open(cookie_file, 'w', encoding='utf-8') as f:
        # Додаємо заголовок, який вимагає формат Netscape
        f.write("# Netscape HTTP Cookie File\n")
        f.write("# http://curl.haxx.se/rfc/cookie_spec.html\n\n")
        
        for line in raw_cookies.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Розбиваємо по будь-яким пробілам
            parts = line.split()
            
            if len(parts) >= 7:
                # З'єднуємо перші 6 частин ТАБУЛЯЦІЄЮ (\t)
                main_parts = parts[:6]
                value = " ".join(parts[6:]) # Значення кука може мати пробіли
                
                fixed_line = "\t".join(main_parts) + "\t" + value
                f.write(fixed_line + "\n")

if __name__ == "__main__":
    save_fixed_cookies()
    print("✅ Куки успішно конвертовано в формат Tab!")
