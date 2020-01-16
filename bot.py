import requests
import json
import re
import base64
import os
import sys
import urllib
from glob import glob

# supress verify False warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AnimeDL:


    @staticmethod
    def parseAppData(page):
        appData = re.findall('appData = {(.*)}', page.text)[0]

        if appData == []:
            exit('[X] AppData Not Found')

        appData = json.loads('{' + appData + '}')
        return appData

    @staticmethod
    def getDownloadSize(fileLink):
        r = requests.head(fileLink)
        return '{:.2f}'.format(int(r.headers.get('content-length')) / pow(10, 6))

    def getIframeSrc(self, page, iframeid = 'embed-responsive-item'):
        return re.findall('iframe.*src="(.*?)"', page)[0]

    def parseMaster(self, fileName):
        masterJson = {}

        with open(fileName, 'r') as fileObj:
            lines = fileObj.read().splitlines()

            for i, line in enumerate(lines):
                # print(line)
                if 'RESOLUTION' in line:
                    resolution = re.findall(',RESOLUTION=(.*?),', line)[0]
                    url = lines[i + 1]

                    masterJson[resolution] = url

        return masterJson

    def grabAnimePage(self):
        pageUrl = input('[?] Enter Page URL : ')
        # pageUrl = "https://www.kickassanime.rs/anime/enen-no-shouboutai-959141"
        print('--------------------------------------------------')

        page = requests.get(pageUrl)

        appData = self.parseAppData(page)
        animeEpisodes = appData['anime']['episodes']
        print('[!] Anime : %s' %(appData['anime']['name']))

        self.animeName = re.sub(r'[^\w]', ' ', appData['anime']['name'])

        return self.grabEpisodePage(animeEpisodes)

    def grabEpisodePage(self, animeEpisodes):
        print('[!] No. of Episodes : %d' %(len(animeEpisodes)))
        print('--------------------------------------------------')

        # reverse the list to that the sort will be in order
        animeEpisodes = animeEpisodes[::-1]

        # episodeRange = ('[>] How many episodes do you wanna download : ')
        
        for episodeNumber in range(len(animeEpisodes)):
            # if episodeNumber > 0:
            #     break

            if os.path.exists('Anime/%s/Episode %d.mp4' %(self.animeName, episodeNumber + 1)):
                print('[:] Skipping : Episode %d' %(episodeNumber + 1))
                continue
            
            print('[>] Grabbing : Episode %d' %(episodeNumber + 1))

            animeEpisodeUrl = 'https://www.kickassanime.rs' + animeEpisodes[episodeNumber]['slug']

            page = requests.get(animeEpisodeUrl)
            appData = self.parseAppData(page)
            
            dustUrl = re.findall("\'(https:\/\/haloani.ru\/dust\/.*?)\'", str(appData))

            try:
                self.getM3U8(dustUrl[0], episodeNumber + 1)
            except IndexError:
                print('[X] Error')
                print('[/] Changing Server')

            print('--------------------------------------------------')
        
    def getM3U8(self, dustUrl, episodeNumber):
        page = requests.get(dustUrl)
        iframeUrls = re.findall('value\=\"https:\/\/haloani\.ru\/(.*?)\/(player.php|embed.php|m.php)\?(.*?)\"', page.text)
        
        selectedServer = ''
        completeUrl = ''
        priority = ['kickassanime', 'html5-hq', 'html', 'sapphire-duck', 'dailymotion']
        
        for p in priority:
            for server, player, link in iframeUrls:
                if server.lower() in p:
                    completeUrl = 'https://haloani.ru/%s/%s?%s' %(server, player, link)
                    selectedServer = p
                    try:
                        self.serverParse(completeUrl, episodeNumber, server = selectedServer)
                        break
                    except IndexError:
                        print('[/] Changing Server')
                        selectedServer = ''
                        continue

            if selectedServer != '':
                break
                
        
    def serverParse(self, iframeUrl, episodeNumber, server = ''):
        print('[#] Server : %s' %(server.title()))

        page = requests.get(iframeUrl)
        try:
            iframeSrc = self.getIframeSrc(page.text)
            if server == 'sapphire-duck':
                completeSrc = "https://haloani.ru/Sapphire-Duck/" + iframeSrc
            elif server == 'dailymotion':
                completeSrc = "https://haloani.ru/dailymotion/" + iframeSrc
            elif server == 'html5' or server == 'html5-hq':
                completeSrc = "https://haloani.ru/html5/" + iframeSrc
            elif server == 'kickassanime':
                completeSrc = "https://haloani.ru/KickAssAnime/" + iframeSrc
            else:
                print('[X] Server Not Supported')
                exit()

            page = requests.get(completeSrc)
        except IndexError:
            print('[>] Download : Page 1')

        if server == 'html5' or server == 'html5-hq':
            qualityLinks = re.findall('\{file\:\"(.*?)\",label:\"(.*?)\"', page.text)    
            try:
                self.quality
            except AttributeError:
                for i in range(len(qualityLinks)):
                    print(' [%d] %s' %(i + 1, list(qualityLinks[i])[1]))
                k = int(input('[?] Quality Selector : '))
                qualitySome = list(qualityLinks[k - 1])[1]
                if '480' in qualitySome:
                    self.quality = '480'
                elif '360' in qualitySome:
                    self.quality = '360'
                elif '720' in qualitySome:
                    self.quality = '720'
                elif '1080' in qualitySome:
                    self.quality = '1080'

            for link, label in qualityLinks:
                if self.quality in label:
                    fileLink = link
           
            # fileLink = list(qualityLinks[k - 1])[0]
            print('[#] URL : %s' %(fileLink))
            os.system('wget -O "Anime/%s/Episode %d.mp4" "%s"' %(self.animeName, episodeNumber, fileLink))
            return
            # return self.downloadEpisodeFromLink("Anime/%s/Episode %d.mp4" %(self.animeName, episodeNumber), fileLink)
            # return
        
        encodedTag = re.findall('decode\(\"(.*?)\"\)', page.text)[0]
        decodedTag = base64.b64decode(encodedTag)

        if server == 'kickassanime':
            animepc_url = 'https:' + re.findall('file:"(.*?)"', str(decodedTag))[0]
            page = requests.get(animepc_url)
            qualityLinks = re.findall('FBQualityLabel="(.*?)"><BaseURL>(.*?)<\/BaseURL>', page.text)
            audioLink = re.findall('value="2"\/><BaseURL>(.*?)<\/BaseURL>', page.text)[0].replace("&amp;", "&")
            try:
                self.quality
            except AttributeError:
                for i in range(len(qualityLinks)):
                    print(' [%d] %s' %(i + 1, list(qualityLinks[i])[0]))
                k = int(input('[?] Quality Selector : '))
                qualitySome = list(qualityLinks[k - 1])[0]
                if '480' in qualitySome:
                    self.quality = '480'
                elif '360' in qualitySome:
                    self.quality = '360'
                elif '720' in qualitySome:
                    self.quality = '720'
                elif '1080' in qualitySome:
                    self.quality = '1080'

            for label, link in qualityLinks:
                if self.quality in label:
                    fileLink = link

            fileLink = fileLink.replace('&amp;', '&')

            print('[#] URL : %s' %(fileLink))
            animeFilePath = "Anime/%s/Episode %d.mp4" %(self.animeName, episodeNumber)
            os.system('wget -O "Temp/audio.mp4" "%s"' %(audioLink))
            os.system('wget -O "%s" "%s"' %(animeFilePath, fileLink))
            os.system('ffmpeg -i "%s" -i "Temp/audio.mp4" -c copy "Temp/output.mp4" -y' %(animeFilePath))
            os.replace("Temp/output.mp4", animeFilePath)
            return

        if server == 'dailymotion':
            dailymotionUrl = re.findall('src\=(.*?)allowfullscreen', str(decodedTag))[0]
            print('[#] URL : %s' %(dailymotionUrl))
            page = requests.get(dailymotionUrl)
            masterM3U8 = re.findall('"qualities":{"auto":\[{"type":"application\\\/x-mpegURL","url":"(.*?)"}]}', page.text)[0]
            masterM3U8 = masterM3U8.replace('\/', '/').replace('\/', '/')
        if server == 'sapphire-duck':
            masterM3U8 = re.findall('file: \"(.*?)\"', str(decodedTag))[0]
            masterM3U8 = masterM3U8.replace('\/', '/').replace('\/', '/')

            print('[#] URL : %s' %(masterM3U8))
        
        with open('Temp/master.m3u8', 'w') as master:
            master.write(requests.get(masterM3U8).text)
            master.close()

        master = self.parseMaster('Temp/master.m3u8')
        try:
            self.quality
        except AttributeError:
            for i in range(len(master)):
                print('   [%d] %s' %(i + 1, list(master)[i]))
            k = int(input('[?] Quality Selector : '))
            qualitySome = list(master)[k - 1]
            if '480' in qualitySome:
                self.quality = '480'
            elif '360' in qualitySome:
                self.quality = '360'
            elif '720' in qualitySome:
                self.quality = '720'
            elif '1080' in qualitySome:
                self.quality = '1080'

        for d in master.keys():
            if self.quality in d:
                indexM3U8 = master[d]

        print('[!] URL : %s' %(indexM3U8))

        with open('Temp/index.m3u8', 'w') as master:
            if server == 'sapphire-duck':
                master.write(requests.get(indexM3U8).text)
            elif server == 'dailymotion':
                hostProxy = re.findall('https:\/\/(.*?)\/', indexM3U8)[0]
                master.write(requests.get(indexM3U8).text.replace('/sec', 'https://%s/sec' %(hostProxy)))
            master.close()

        return self.downloadEpisodeFromM3U8(episodeNumber)

    def downloadEpisodeFromLink(self, file_name, link, debug = True):
        with open(file_name, "wb") as f:
            response = requests.get(link, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None: # no content length header
                f.write(response.content)
            else:
                print('[@] File : {}'.format(file_name))
                print('[@] Size : {:.2f} MB'.format(int(total_length) / pow(10, 6)))
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(100 * dl / total_length)
                    if debug:
                        sys.stdout.write("\r[>] Downloaded : {}%" .format(done))
                        sys.stdout.flush()
        if debug and total_length is not None:
            print()
        if total_length is None:
            os.remove(file_name)
        print('[#] File : Saved')

    def downloadEpisodeFromM3U8(self, episodeNumber):
        print('[>] Downloading Episode %d.mp4' %(episodeNumber))
        if not os.path.exists('Anime/%s' %(self.animeName)):
            os.mkdir('Anime/%s' %(self.animeName))

        os.system('ffmpeg -y -hide_banner -loglevel info -protocol_whitelist file,http,https,tcp,tls,crypto -i "Temp/index.m3u8" -threads 8 -c copy -bsf:a aac_adtstoasc "Anime/%s/Episode %d.mp4"' %(self.animeName, episodeNumber))

if __name__=="__main__":
    bot = AnimeDL()
    bot.grabAnimePage()