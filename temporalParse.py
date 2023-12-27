from mwparserfromhtml import HTMLDump
import html2text
from dateparser import parse
import os
from bs4 import BeautifulSoup
import spacy, re
#import en_core_web_trf

import tarfile

html_file_path = "C:\\Users\\stephen\\Documents\\enwiki-NS0-20231020-ENTERPRISE-HTML.json.tar.gz"

def extractTarArticleInfo(filePath):
    with tarfile.open(filePath, mode="r:gz") as tf:
        while True:
            member = tf.next()
            if member is None:
                break
            if member.isfile():
                print(member.name)

extractTarArticleInfo(html_file_path)

html_dump = HTMLDump(html_file_path, max_article=400)

script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
rel_path = "Tests\\htmltest.html"
abs_file_path = os.path.join(script_dir, rel_path)



class TemporalParser:
    def __init__(self):
        self.TYPE_MAIN_TITLE = "MAIN_TITLE"
        self.TYPE_MAIN_IMAGE_URL = "MAIN_IMAGE_URL"
        self.TYPE_TITLE = "TITLE"
        self.TYPE_PARAGRAPH = "PARAGRAPH"
        self.TYPE_IMAGE = "IMAGE"
        self.TYPE_TABLE = "TABLE"
        self.TYPE_QUOTE = "QUOTE"
        self.TYPE_SUBTITLE = "SUBTITLE"
        self.TYPE_SUB_SUBTITLE = "SUB_SUBTITLE"
        self.TYPE_LIST = "LIST"
        self.TYPE_LIST_ITEM = "LIST_ITEM"
        self.LIST_TYPE_BULLETED = "BULLETED"
        self.LIST_TYPE_NUMBERED = "NUMBERED"
        self.LIST_TYPE_INDENTED = "INDENTED"
        self.saveSections = []
        self.sectionLinks = []
        self.sectionEvents = []
        # track to number of characters for the current section so we know where the link should be inserted
        self.linkOffset = 0
        self.soup = None
        self.currentSection = None
        self.tableHeader = []
        self.tableRows = []
        self.currentRow = []
        self.rowSpan = []
        self.processingTable = False
        self.p = re.compile(r'\[\d+\]')

        self.nlp = spacy.load("en_core_web_trf")

    def parse(self, soup):
        self.soup = soup
        self.soup.find(id="References").findParent(name="section").clear()
        self.soup.find(id="External_links").findParent(name="section").clear()
        self.generateSection(self.TYPE_TITLE, self.soup.find_all("title")[0].string)

        for bodychild in self.soup.find('body').children:
            self.parseNodes(bodychild)

    def generateSection(self, type, text):
        self.linkOffset = 0
        self.currentSection == None
        nodeSection =  { 'type': type, 'text': text }
    
        if (nodeSection):
            self.saveSections.append(nodeSection)
        print(nodeSection)

    def generateLinkText(self, linkNode):
        strippedText = linkNode.text.strip()

        if not linkNode.attrs['href'].startswith("./File:"):
        
            if (self.processingTable):
                self.sectionLinks.append({ 'section': len(self.saveSections),
                                   'article': linkNode.attrs['href'], 'start': (self.linkOffset + 1),
                                    'end': (self.linkOffset + len(strippedText) + 1),
                                    'column': len(self.currentRow), 'row': len(self.tableRows) } )
            else:
                self.sectionLinks.append({ 'section': len(self.saveSections),
                                   'article': linkNode.attrs['href'], 'start': (self.linkOffset + 1),
                                    'end': (self.linkOffset + len(strippedText) + 1) } )

        return strippedText
    
    def parseChildren(self, node, leading=None, trailing=None):
        nodeText = ""
        for sectionChild in node.children:
            nodeText += self.parseNodes(sectionChild)
            self.linkOffset = len(nodeText)

        if nodeText.strip() == "":
            return ""
        if leading :
            nodeText = leading + nodeText
        if trailing:
            nodeText = nodeText + trailing
        self.linkOffset = len(nodeText)
        return nodeText

    def parseNodes(self,node):
        nodeText = ""
        # print(node.name)
        if (node.name == None):
            if node.text.startswith("<span"):
                return ""
            return node.text.strip()
        if (node.name == "p"):
            self.currentSection = self.TYPE_PARAGRAPH
            for bodychild in node.children:
                
                newText = self.parseNodes(bodychild)
                if newText != "":
                    nodeText += newText + " "
                    self.linkOffset = len(nodeText)
            self.generateSection(self.TYPE_PARAGRAPH,nodeText)

        elif (node.name == "a"):
            return self.generateLinkText(node)
        
        elif (node.name == "b"):
            return self.parseChildren(node, "**", "**")
        
        elif (node.name == "i"):
            return self.parseChildren(node, "*", "*")
            
        elif (node.name == "h2"):
            self.generateSection(self.TYPE_TITLE, node.text.strip())

        elif (node.name == "h3"):
            self.generateSection(self.TYPE_SUBTITLE, node.text.strip())

        elif (node.name == "h4"):
            self.generateSection(self.TYPE_SUB_SUBTITLE, node.text.strip())

        elif (node.name == "section" or node.name == "span"):
            nodeText = self.parseChildren(node)
            #if nodeText != "":
            #    self.generateSection(self.TYPE_PARAGRAPH, nodeText)

        elif (node.name == "ul" or node.name == "ol" or node.name == "dl"):
            nodeText = self.parseChildren(node)
            if nodeText != "":
                self.generateSection(self.TYPE_LIST, nodeText)

        elif (node.name == "li" or node.name == "dt" or node.name == "dd"):
            return self.parseChildren(node, " - ", "\n")
        
        elif (node.name == "blockquote"):
            return self.parseChildren(node, " > ")
        
        elif (node.name == "table"):
            if "infobox" in node.attrs['class']:
                return ""
            else: 
                self.parseTable(node)
        elif (node.name == "img"):
            return ""
        else :
            return ""
        
        return ""
    
    def parseTable(self, table):
        self.tableHeader = []
        self.tableRows = []
        self.currentRow = []
        self.rowSpan = []
        self.processingTable = True
        for sectionChild in table.children:
            self.parseTablePart(sectionChild)

        nodeSection =  { 'type': self.TYPE_TABLE, 'headder': self.tableHeader, 'rows': self.tableRows }
    
        if (nodeSection):
            self.saveSections.append(nodeSection)
        self.processingTable = False
        print(nodeSection)
    
    def parseTablePart(self, node):
        if (node.name == "thead" or node.name == "tbody"):
            for sectionChild in node.children:
                self.parseTablePart(sectionChild)
        elif (node.name == "tr"):
            for sectionChild in node.children:
                self.parseTablePart(sectionChild)

        elif (node.name == "th"):
            self.tableHeader.append( self.parseChildren(node))
            self.rowSpan.append(0)
        elif (node.name == "td"):
            
            while self.rowSpan[len(self.currentRow) ] > 1 :
                self.rowSpan[len(self.currentRow) ] -= 1
                self.currentRow.append(self.tableRows[-1][len(self.currentRow) ])
            
            self.currentRow.append(self.parseChildren(node))
            if 'rowspan' in node.attrs:
                self.rowSpan[len(self.currentRow) - 1] = int(node.attrs['rowspan'])
            else:
                self.rowSpan[len(self.currentRow) - 1] = 1

            # if we have a complete row append
            if (len(self.currentRow) >= len(self.tableHeader)):
                self.tableRows.append(self.currentRow)
                self.currentRow = []

    def parseEvnets(self):
        for idx, section in enumerate(self.saveSections):
            if (section['type'] == self.TYPE_TABLE):
                for rowIdx, row in enumerate(section['rows']):
                    for columnIdx, cell in enumerate(row):
                        self.extract_events_spacy(cell, idx, rowIdx, columnIdx)
            else:
                self.extract_events_spacy(str(section["text"]), idx)

    def generateEvent(self, idx, rowIdx, columnIdx, date, startPos, endPos, dText, desc):
        self.linkOffset = 0
        self.currentSection == None
        nodeSection =  { 'section': idx, 'rowIdx': rowIdx, 'columnIdx': columnIdx, 'date': date, 'startPos': startPos, 'endPos': endPos, 'dText': dText, 'desc': desc }
    
        if (nodeSection):
            self.sectionEvents.append(nodeSection)
        print(nodeSection)

    def dep_subtree(self, token, dep):
        deps = [child.dep_ for child in token.children]
        child = next(filter(lambda c: c.dep_ == dep, token.children), None)
        if child != None:
            return " ".join([c.text for c in child.subtree])
        else:
            return ""


    def extract_events_spacy(self, text, idx, rowIdx=None, columnIdx=None):

        doc = self.nlp(text)
        for ent in filter(lambda e: e.label_ == 'DATE', doc.ents):

            start = parse(ent.text)
            if start == None:
                # could not parse the dates, hence ignore it
                self.generateEvent( idx, rowIdx, columnIdx, None, ent.start_char, ent.end_char, ent.text, None)
                print('Event Discarded: ' + ent.text)
            else:
                current = ent.root
                desc = ""
                while current.dep_ != "ROOT":
                    current = current.head
                    desc = " ".join(filter(None, [
                        self.dep_subtree(current, "nsubj"),
                        self.dep_subtree(current, "nsubjpass"),
                        self.dep_subtree(current, "auxpass"),
                        self.dep_subtree(current, "amod"),
                        self.dep_subtree(current, "det"),
                        current.text,
                        self.dep_subtree(current, "acl"),
                        self.dep_subtree(current, "dobj"),
                        self.dep_subtree(current, "attr"),
                        self.dep_subtree(current, "advmod")]))
                self.generateEvent(idx, rowIdx, columnIdx, start, ent.start_char, ent.end_char, ent.text, desc)
        return



with open(abs_file_path) as f:
    textLines = f.readlines()

text = ""
for line in textLines:
    tempLine = line.replace("\\n", "\n").strip() + " "
    # replace double escaped characters
    tempLine = re.sub(r"(\\')", "'", tempLine)
    text += tempLine



hToText = html2text.HTML2Text()
soup = BeautifulSoup(text, features="html.parser")
temporParse = TemporalParser()
htmltext = soup.encode('utf-8').decode('utf-8','ignore')
temporParse.parse(soup)

temporParse.parseEvnets()



soup.find_all("section")[0].find("table", "infobox")

for section in soup.find_all("section"):
    hasInfobox = section.find("table", "infobox")
    if (hasInfobox):
        saveSections.append(section)

    print(article.get_plaintext( skip_categories=False, skip_transclusion=False, skip_headers=False))

newText  = hToText.handle(htmltext)


#for article in html_dump:
#    if article.title == "189th Infantry Brigade (United States)":
#        print(article.get_plaintext( skip_categories=False, skip_transclusion=False, skip_headers=False))
#        
#    print(article.title)


