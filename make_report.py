"""Create Japanese submission PDF and editable Markdown from measured results.
Run after run_experiment.py: python make_report.py
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

OUTPUT = Path('results')
# EDIT THESE THREE VALUES BEFORE SUBMITTING (no credentials are needed).
OMNI_ACCOUNT = '提出前にアカウント名へ変更'
GITHUB_URL = '［提出前にURLを記入］'
YOUTUBE_URL = '［新しい比較動画をアップロード後にURLを記入］'
OUTPDF = Path(f'説明資料_PAI最終課題_{OMNI_ACCOUNT}.pdf')
OUTMD = Path('レポート文章_編集用.md')

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
FONT = 'HeiseiKakuGo-W5'
NAVY = colors.HexColor('#203650')
TEAL = colors.HexColor('#087f70')
SLATE = colors.HexColor('#516378')
PALE = colors.HexColor('#f1f5f8')

styles = {
 'title':ParagraphStyle('title',fontName=FONT,fontSize=17,leading=24,textColor=NAVY,spaceAfter=9),
 'subtitle':ParagraphStyle('sub',fontName=FONT,fontSize=10,leading=16,textColor=SLATE,spaceAfter=16),
 'h2':ParagraphStyle('h2',fontName=FONT,fontSize=12,leading=19,textColor=NAVY,spaceBefore=15,spaceAfter=8),
 'body':ParagraphStyle('body',fontName=FONT,fontSize=9.1,leading=16,textColor=NAVY,spaceAfter=8),
 'small':ParagraphStyle('small',fontName=FONT,fontSize=8.2,leading=13.6,textColor=SLATE,spaceAfter=6),
 'th':ParagraphStyle('th',fontName=FONT,fontSize=8.4,leading=13,textColor=colors.white),
 'cell':ParagraphStyle('cell',fontName=FONT,fontSize=8.2,leading=13,textColor=NAVY),
 'footer':ParagraphStyle('footer',fontName=FONT,fontSize=8,leading=12,textColor=SLATE),
}

def P(s,key='body'):
 return Paragraph(escape(s),styles[key])

def table(headers,rows,widths):
 cells=[[P(x,'th') for x in headers]]+[[P(str(x),'cell') for x in row] for row in rows]
 t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([
     ('BACKGROUND',(0,0),(-1,0),NAVY),
     ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
     ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
     ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
     ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
     ('LINEBELOW',(0,-1),(-1,-1),0.4,colors.HexColor('#cedbe5')),
 ]))
 return t

def footer(canvas,doc):
 canvas.saveState()
 canvas.setStrokeColor(colors.HexColor('#dce3eb'))
 canvas.line(16*mm,16*mm,194*mm,16*mm)
 canvas.setFont(FONT,7.6)
 canvas.setFillColor(SLATE)
 canvas.drawString(17*mm,12*mm,'Physical AI 最終課題  |  Q-learning 2D格子シミュレーション')
 canvas.drawRightString(193*mm,12*mm,str(doc.page))
 canvas.restoreState()

def main():
 data=json.loads((OUTPUT/'summary.json').read_text(encoding='utf-8'))
 rr={r['condition']:r for r in data['scenario_results']}
 f=lambda label:rr[label]
 original=f('Original environment / trained AI')
 off_old=f('Add (3,6) / original AI')
 off_new=f('Add (3,6) / retrained AI')
 on_old=f('Add (6,2) / original AI')
 on_new=f('Add (6,2) / retrained AI')
 random=f('Original environment / random')

 story=[]
 story += [P('Physical AI 最終課題 説明資料','title'),P('Q-learningによる自律移動ロボットの障害物回避と、環境変化への再学習の比較','subtitle')]
 story += [P('1. 課題の目的','h2'),
   P('8×8の2次元格子環境で、ロボットが障害物を避けてスタート (0,0) からゴール (7,7) に移動する課題を設定した。強化学習（Q-learning）で行動方策を獲得し、障害物を増やした場合に、元のAIと再学習したAIの動作がどのように異なるか比較した。'),
   P('本作品は簡易的な離散格子シミュレーションであり、実機やGazeboなどの物理エンジンを使用したものではない。','small')]
 story += [P('2. 開発環境・実装内容','h2'),
   table(['項目','設定'],[
       ('実行環境','Google Colab または PythonのCPU環境'),
       ('開発言語','Python（NumPy、Pillow、FFmpeg）'),
       ('強化学習','表形式のQ-learning、6,000エピソード、乱数シード2026'),
       ('状態と行動','状態＝格子上の位置、行動＝上下左右の4種類'),
       ('報酬','ゴール：+10、障害物／壁：-1、通常移動：-0.08'),
       ('評価','最大40ステップ、固定開始位置での到達可否・ステップ数'),
       ],[44*mm,145*mm])]
 story += [P('3. 実験条件','h2'),
   P('実験A：元の12個の障害物で学習・評価する。実験B：元のAIを保持したまま (3,6) に障害物を1個追加し、再学習したAIとも比較する。実験C：元の経路上にある (6,2) に障害物を追加し、元のAIと再学習したAIを比較する。'),
   P('追加障害物は実験ごとに元の12個の配置へ戻しており、(3,6) と (6,2) を同時には追加していない。','small')]
 story.append(PageBreak())
 story += [P('4. 比較実験の結果','h2')]
 items=[
    ('元の環境／ランダム',random),
    ('元の環境／学習済みAI',original),
    ('(3,6)追加／元のAI',off_old),
    ('(3,6)追加／再学習AI',off_new),
    ('(6,2)追加／元のAI',on_old),
    ('(6,2)追加／再学習AI',on_new),
 ]
 rows=[]
 for label,r in items:
    rows.append((label,f"{r['success_rate_percent']:.0f}%",str(r['one_run_steps']),str(r['one_run_blocked'])))
 story.append(table(['条件','到達率*','行動数','移動不能回数'],rows,[81*mm,30*mm,30*mm,48*mm]))
 story.append(Spacer(1,6*mm))
 story.append(P('*到達率：固定のスタート・ゴールで100回実行した値。学習済みAIは決定論的で、100回の結果は独立した100環境での性能を意味しない。','small'))
 story.append(P('元のAIは14ステップでゴールへ到達した。(3,6) は元の経路上になかったため、追加後も元のAIは14ステップで到達した。一方、(6,2) は元の経路上にあり、追加後は元のAIが同じ方向への移動を繰り返して40ステップ以内に到達できなかった。再学習後のAIは14ステップで到達した。'))
 pic = OUTPUT/'route_comparison.png'
 if pic.exists():
    story.append(Image(str(pic),width=177*mm,height=77.4*mm))
    story.append(P('図：左から、元の環境、(3,6)追加、(6,2)追加。各条件とも追加前に学習した元のAIを評価した軌跡。','small'))
 story += [P('5. 考察','h2'),
   P('今回の結果から、環境変化の位置によって元の行動方策への影響が異なることが分かった。経路外の障害物を増やしても元の行動には影響しなかったが、経路上の障害物が増えると元の行動方策が失敗した。再学習によって別の経路を獲得できたことから、固定環境での再学習の有効性が確認できた。')]
 story.append(PageBreak())
 story += [P('6. 工夫した点','h2'),
  P('① ただ学習済みAIを動かすだけでなく、学習前後および障害物変更前後を同じコードで再現できるようにした。'),
  P('② 経路外 (3,6) と経路上 (6,2) の2条件を分けることで、環境変化の位置によって影響が異なることを評価した。'),
  P('③ 乱数シードを固定し、再学習と元の学習済み方策の比較に同じ環境条件を使用した。'),
  P('④ ColabのCPUで実行可能な軽量な実装とし、評価結果をCSV・動画・画像として保存した。')]
 story += [P('7. 限界と今後の展望','h2'),
  P('本課題は離散的な2次元格子上の実験であり、ロボットアームや車輪の運動学、連続空間、センサー雑音、物理衝突などは表現していない。また、固定したスタート・ゴールでの評価のみなので、未知のマップでも成功するとは言えない。今後は移動開始位置や障害物配置をランダム化し、学習せずに新環境へ適応できるかを評価するとともに、物理シミュレータへの拡張を検討する。')]
 story += [P('8. 提出情報','h2'),
  P('GitHub 公開リポジトリ：' + GITHUB_URL),
  P('YouTube 比較動画：' + YOUTUBE_URL),
  P('利用した学習・実行環境：Google Colab／CPU'),
  P('本コードは先に作成した学習サンプルを基に、生成AIの補助を利用して比較実験の実装・整理を行った。結果は同梱コードの実行出力に基づく。','small')]
 story += [P('提出前の確認','h2'),
  P('・PDFファイル名の「提出前にアカウント名へ変更」を、実際のomnicampusアカウント名に置換する。'),
  P('・動画を再生して内容を確認し、YouTubeの1～3分の要件を満たすことを確認する。'),
  P('・GitHubの公開設定（Public）と提出URLを確認する。')]
 doc=SimpleDocTemplate(str(OUTPDF),pagesize=A4,rightMargin=17*mm,leftMargin=17*mm,
                       topMargin=19*mm,bottomMargin=20*mm,title='Physical AI最終課題 説明資料',author='Physical AI final project')
 doc.build(story,onFirstPage=footer,onLaterPages=footer)

 md=f'''# Physical AI最終課題 説明資料

## Q-learningによる自律移動ロボットの障害物回避と環境変化への対応

### 目的
8×8の2次元格子環境でQ-learningによるロボットの障害物回避を実装する。元の障害物配置に加え、経路外(3,6)、経路上(6,2)のそれぞれに障害物を追加し、変更前のAIと再学習AIを比較した。

### 方法
- Colab（CPU）／Python／NumPy／Pillow／FFmpeg
- 表形式Q-learning、学習6000エピソード、乱数シード2026
- 上下左右4行動。ゴール:+10、壁・障害物:-1、移動:-0.08
- 既存AIを保持したまま地図を変更して評価し、変更後の環境で再学習する。

### 結果
| 条件 | 到達率（固定位置100回反復） | 行動数 | 移動不能回数 |
|---|---:|---:|---:|
'''
 for label,r in items:
    md+=f"| {label} | {r['success_rate_percent']:.0f}% | {r['one_run_steps']} | {r['one_run_blocked']} |\n"
 md+='''
### 考察
(3,6)は元のAIの経路上にないため、元のAIの到達に影響しなかった。一方(6,2)は経路上なので、元のAIが移動不能となったが、再学習したAIは14ステップで到達した。環境変化の位置によって再学習の必要性が変わることを確認した。

### 工夫
- 経路外と経路上に障害物を加えた2条件で比較した。
- 元のAIを再学習で上書きせず保持して、同じ変更後の環境で公平に比較した。
- 乱数シードを固定し、CSV・MP4・静止画像に自動保存した。

### 限界
実機ではなく、離散2D格子の簡易シミュレーション。固定開始位置・固定ゴールの決定論的AIを100回反復した数値であり、未知マップでの一般化性能は示さない。物理エンジン、センサーノイズ、連続座標は未実装。

### 公開情報（提出前に記入）
- GitHub: ［公開URL］
- YouTube: ［今回作成した新しい比較動画URL］
- 作成補助：生成AIを利用
'''
 OUTMD.write_text(md.replace('［公開URL］',GITHUB_URL).replace('［今回作成した新しい比較動画URL］',YOUTUBE_URL),encoding='utf-8')
 print('Generated PDF:',OUTPDF,'size=',OUTPDF.stat().st_size)
 print('Generated editable text:',OUTMD)

if __name__=='__main__':
 main()
