# archforge-mcp タスク管理

進め方: 上から順にストーリー単位で完了させる。実装再開時は一番上の未完了ストーリーの一番上の🔲から着手。

各ストーリーはユーザー価値を主語にした単位（「〜できる」）。その下の「タスク」は実装都合の技術的な分解。状態は 🔲未着手 / 🔶一部実装（動くはずだが未検証、または一部のみ実装） / ✅完了（実機で動作確認済み）の3段階。

**注記（2026-08-31）**: 姉妹プロジェクト`archforge`との最大の違いは、「問題を生成する」「レビューする」という判断そのものが自前コードの中に存在しないこと。`bank.py`/`schema.py`/`practice.py`は`archforge`からそのまま移植済みで、ローカルの保存・出題・採点ロジックとしてはこのプロジェクトでも変わらず有効（採点にAPI呼び出しは元々不要だった部分）。一方で、`archforge`の`generate.py`（マルチエージェント生成本体）・`domain_agent_system_prompt.jinja`・`reviewer_system_prompt.jinja`に相当するコードは**移植のしようがない**——生成とレビューはMCPクライアント側（Claude Code/Desktop）のセッションの中で行われるものだから。そのためこのTASKS.mdでは、(1) バンク操作をMCPツールとして公開するストーリー群、(2) `jinja`テンプレート相当をプロンプトテンプレートとして公開し生成品質のブレを抑えるストーリー、(3) 既に移植済みのオフラインpractice/statsの位置づけを明確化するストーリー、(4) 会話の中で出題から解説まで**追加のAPI課金なしで**完結できるという、このアーキテクチャならではの価値を明示するストーリー、(5) セットアップ・接続ストーリー、に分けて整理した。`unattempted`ツールが返す問題には正解（`correct_indices`）が含まれる（会話内でエージェント自身が採点するため）。これはbank.jsonの生データをそのまま返す設計上の帰結であり、ユーザーに正解を早出ししないための制御はコード側の隠蔽ではなくプロンプト側の指示に委ねている点を明記しておく。

## ストーリー1: 生成した問題をMCP経由でバンクに保存できる
状態: ✅ 完了（2026-08-31、自動テスト4件＋実際の`data/bank.json`への手動確認済み）

**目的**: Claude Code/DesktopなどMCPクライアント側のセッションで生成・レビュー済みの問題を、MCPツール経由で`bank.json`に永続化できる。以降の全ストーリーの土台。

**DoD**: MCPクライアントから`add_questions`ツールを問題リスト（ドメイン込み）で呼ぶと、`id`/`created_at`/空の`attempts`が付与された状態で`bank.json`に追記保存される。スキーマ違反（必須フィールド欠如・型不一致など）は`ToolError`として返り、バンクは書き換わらない。

- [x] `archforge_mcp/server.py`: `from fastmcp import FastMCP`でサーバーインスタンスを作成するモジュールを新規作成
- [x] `add_questions`ツール: 引数は`schema.ReviewedQuestion`のリスト（Pydanticでバリデーション）。内部で`Bank.load` → `Bank.add_questions` → `Bank.save`を呼ぶ
- [x] Pydanticのバリデーションエラーを`fastmcp.exceptions.ToolError`に変換して返す（fastmcpが引数を型ヒントに対して自動検証し、失敗時に自前で`ToolError`を投げてくれるため、手動での変換コードは不要だった。実機確認済み）
- [x] `if __name__ == "__main__": mcp.run()`でstdioサーバーとして起動できるようにする
- [x] fastmcpのin-processクライアント（`Client(mcp)`）を使った`server.py`用の自動テストを書く（`test_server.py`、正常系2件＋スキーマ違反2件の計4件）
- [x] 手動確認: `Client(mcp)`から`add_questions`を1問分呼び、`data/bank.json`に反映されることを確認
- [x] 手動確認: 必須フィールド欠如などの不正な入力で`add_questions`を呼び、`ToolError`が返り`bank.json`が書き換わらないことを確認する

## ストーリー2: まだ解いていない問題をMCP経由で取得できる
状態: ✅ 完了（2026-08-31、自動テスト4件＋実際の`data/bank.json`への手動確認済み）

**依存**: ストーリー1（バンクにデータがある前提で意味を持つ）

**目的**: MCPクライアント側が「まだ出題していない問題」を把握できるようにする。これにより (1) 追加生成の前に該当ドメインに何問溜まっているか確認して重複生成を避けられる、(2) 会話の中でエージェントに未回答問題を出題してもらえる、という2通りの使い方ができる。

**DoD**: `unattempted`ツールを`domain`指定あり/なしで呼ぶと、未回答の問題（正解の`correct_indices`を含む全フィールド）が返る。

- [x] `unattempted`ツール: `domain: str | None`引数、`Bank.unattempted`をラップ
- [x] 返り値に正解を含める設計であることをツールのdocstringに明記する（会話内出題でエージェント自身が採点するために必要。ユーザーに早出ししない制御はエージェント側の振る舞いに委ねる）

## ストーリー3: Bankをステートフルなクラスにする（内部リファクタリング）
状態: ✅ 完了（2026-08-31、`archforge-mcp`のみ対象。姉妹プロジェクト`archforge`の`bank.py`は据え置き）

**依存**: なし。ユーザーから見える挙動（DoD）は変わらない純粋な内部リファクタリング

**目的**: ストーリー1・2の実装で、`add_questions`/`unattempted`ツールがどちらも`current = bank.load_bank()` → 操作 → `bank.save_bank(current)`という同じ手順を毎回書く必要があった。`Bank`に`self.questions`を持たせて`current`の持ち回しは無くしたが、それだけだと今度は`bank.load()` → 操作 → `bank.save()`という手順が呼び出し側（`server.py`/`practice.py`）に残ってしまう。これも`Bank`側に隠蔽し、呼び出し側は`bank.add_questions(...)`/`bank.unattempted(...)`のように操作を呼ぶだけで済むようにする（load/saveの存在を意識しなくてよい）。

**DoD**: `Bank`の4操作（`add_questions`/`unattempted`/`record_attempt`/`domain_stats`）が、それぞれ自分の中で`load()`を呼んでから処理し（`add_questions`/`record_attempt`は処理後に`save()`も呼ぶ）、呼び出し側は`load()`/`save()`を明示的に呼ぶ必要が無い。`load()`/`save()`自体はテストなど手動制御したい場合のために公開メソッドとして残す。既存の全自動テスト（`test_bank.py`/`test_practice.py`/`test_server.py`）が新APIに合わせて書き直された上でパスし、実機の`data/bank.json`に対しても`add_questions`→`unattempted`が変わらず動くことを確認する。

- [x] `bank.py`: `Bank.__init__`で`self.questions: list[Question] = []`を持たせ、`add_questions`/`unattempted`/`record_attempt`/`domain_stats`の内部冒頭で`self.load()`を呼び、`add_questions`/`record_attempt`は処理後に`self.save()`も呼ぶ（`load_bank`→`load`、`save_bank`→`save`も改名。`load`/`save`自体は公開メソッドのまま残す）
- [x] `server.py`: `add_questions`/`unattempted`ツールから明示的な`bank.load()`/`bank.save()`呼び出しを削除（`bank.add_questions(...)`/`bank.unattempted(...)`を呼ぶだけに）
- [x] `practice.py`: `run_practice`から明示的な`bank.load()`/`bank.save()`呼び出しを削除
- [x] `test_bank.py`/`test_practice.py`/`test_server.py`を新APIに合わせて書き直す（`test_server.py`の`_isolated_bank`フィクスチャは`bank_path`の差し替えのみでよくなった。各操作が自分で`load()`するため、モジュール単位で共有される`bank`インスタンスの前テストの残留状態が漏れ込む心配がない）
- [x] `uv run pytest`で全30件がパスすることを確認
- [x] 手動確認: 実際の`data/bank.json`に対して`add_questions`→`unattempted`を実行し、リファクタリング前と同じ結果になることを確認

## ストーリー4: 解答した結果をMCP経由で記録できる
状態: ✅ 完了（2026-08-31、自動テスト2件＋実際の`data/bank.json`への手動確認済み）

**依存**: ストーリー1、2、3

**目的**: MCPクライアントとの会話の中で問題に答えたとき、その結果を`bank.json`に記録し、以後その問題が「未回答」として出題されないようにする。

**DoD**: `record_attempt`ツールを`(qid, given_indices, correct)`で呼ぶと`bank.json`の`attempts`に追記される。存在しない`qid`を渡すと`ToolError`になる。

- [x] `record_attempt`ツール、`Bank.record_attempt`をラップ
- [x] `Bank.record_attempt`が投げる`KeyError`を`ToolError`に変換（`add_questions`のスキーマ違反と違い、こちらはfastmcpが自動でやってくれないので`try/except`で明示的に変換する）
- [x] 手動確認: 会話内で1問出題→回答→`record_attempt`→再度`unattempted`を呼び、対象問題が結果に含まれなくなっていることを確認
- [x] 手動確認: 存在しない`qid`で`record_attempt`を呼び、`ToolError`になることを確認する

## ストーリー5: 自分の弱点ドメインを会話の中で知ることができる
状態: 🔲 未着手

**依存**: ストーリー4（意味のある集計には記録データが必要。バンクが空でも動作自体は落ちない）

**目的**: 「自分の弱点は？」とチャットで聞くと、ドメイン別正答率と本番の出題比率を踏まえた回答がもらえる。

**DoD**: `domain_stats`ツールを呼ぶと、ドメインごとの`total`/`attempted`/`correct`に加えて`config.DOMAINS`の本番重みが一緒に返り、エージェントが本番重み順（27/18/20/20/15%）に並べて解釈できる。

- [ ] `domain_stats`ツール、`Bank.domain_stats`をラップ
- [ ] レスポンスに`config.DOMAINS`の重み情報も含める（エージェントが呼び出しのたびに正しい重みを覚えておく必要がないようにする）

## ストーリー6: 毎回ブレない質で問題を生成してもらえる
状態: 🔲 未着手

**依存**: ストーリー1（生成結果を`add_questions`が要求するJSON構造に合わせる必要があるため）

**目的**: `archforge`の`domain_agent_system_prompt.jinja`/`reviewer_system_prompt.jinja`に相当する仕組みがないと、Claude Code側は毎回思いつきの指示で生成することになり、シナリオの粒度・distractorの質・`grounding_notes`の厳密さがセッションごとにばらつく。`@mcp.prompt()`でテンプレートを公開し、MCPクライアント側が一貫した生成・レビュー指示を得られるようにする（実装手段は`@mcp.prompt()`によるプロンプトテンプレート配信）。

**DoD**: `generate_domain_questions`と`review_questions`という2つの`@mcp.prompt()`が公開される。MCPクライアントからこれらを呼ぶと、archforgeの2つのjinjaテンプレートと同等の内容（シナリオ必須・distractorは尤もらしく・`select_count_hint`と`correct_indices`の件数一致・`grounding_notes`は具体的根拠必須・重複シナリオ回避・レビュー基準）を含むプロンプト文字列が返り、そのまま`add_questions`が要求するJSON構造で生成するよう誘導する。

- [ ] archforgeの`domain_agent_system_prompt.jinja`の内容をベースに、web_search前提の文言を「利用可能な検索能力があれば公式ドキュメントを参照すること」のような一般化した文言に書き換える（呼び出し元エージェントがweb_searchを持つとは限らないため）
- [ ] archforgeの`reviewer_system_prompt.jinja`相当も同様に一般化して移植
- [ ] fastmcpの`@mcp.prompt()`は関数引数がそのままプレースホルダーになるため、jinjaファイルを持ち込まずPython関数内でf-stringとして組み立てる方針とする（jinja2を新規依存に追加しない）
- [ ] `generate_domain_questions(domain: str, count: int)`として公開。`domain`は`config.DOMAINS`に定義された名前から選ぶよう誘導する
- [ ] `review_questions()`を公開
- [ ] 出力形式（`add_questions`ツールが要求するJSON構造）をプロンプト内に明記し、エージェントが生成後そのまま`add_questions`を呼び出せる形にする
- [ ] 検討したが見送った項目: 合計N問を`config.DOMAINS`の重みでドメイン別に配分計算する専用ツール（archforgeの`_counts_per_domain`相当）。v1ではプロンプト内に重み表を埋め込み、配分計算自体はエージェントに委ねる。実際に配分が偏るようなら着手する
- [ ] `schema.py`のコメントに残る`archforge`旧ストーリー番号の参照（"story 2's web_search generation"）、`practice.py`の"story 8"参照、`config.py`の（archforge-mcpにはまだ存在しない）`DESIGN.md`参照について、このプロジェクト自身のストーリー番号・実情に書き換えるか、移植時の経緯としてそのまま残すかを決めて反映する

## ストーリー7: 会話の中で出題〜解答〜解説まで、追加のAPI課金なしで一気通貫にできる
状態: 🔲 未着手

**依存**: ストーリー2、4

**目的**: `archforge`では「解説を見る」に専用の`explain.py`と追加のAPI呼び出しが必要だった（ストーリー8相当、都度課金が発生する）。`archforge-mcp`では、出題しているエージェント自身がユーザーのClaude Pro/Maxサブスクリプションで動いているセッションそのものなので、`unattempted`で出題→ユーザーが回答→エージェントが`grounding_notes`を根拠にその場で正誤と解説を返す、という流れを**追加のAPI呼び出しを一切発生させずに**実現できる。これはこのアーキテクチャならではの価値なので独立したストーリーとして明示する。なお、解説の質（`grounding_notes`の具体性）自体はストーリー6のプロンプトテンプレートが左右するが、本ストーリーの`practice_session`プロンプトはストーリー6の成果物がなくても既存バンクの`grounding_notes`を使って動作するため、技術的な依存関係としては挙げていない。

**DoD**: Claude Codeに接続した状態で「出題して」と頼むと、`unattempted`→出題→ユーザー回答→`record_attempt`→（希望すれば）`grounding_notes`に基づく解説、という流れが1つの会話内で完結する。`practice_session`プロンプトがユーザー回答前に正解を明かさないことをエージェントへの指示として明記しており、実機確認でもその通りに振る舞うことを確認する（コードによる保証ではなく、プロンプト指示とその遵守の観測確認である点に注意）。

- [ ] 上記の流れを誘導する`@mcp.prompt()`（例: `practice_session`）を用意し、出題→採点→（希望時のみ）解説の手順と、ユーザーの回答前に正解を明かさないことをエージェントへの指示として明記する
- [ ] `practice_session`プロンプトの中で、`config.EXAM_NAME`/`DOMAINS`を踏まえた出題ドメインの選び方（省略時は全ドメインからランダム、指定時はそのドメインに絞る）も指示する
- [ ] 実機（Claude Code接続）で「出題→誤答→解説→次の問題」を1周動作確認する

## ストーリー8: MCPサーバーに接続していなくても、ローカルで問題を解いたり成績を確認できる
状態: 🔶 一部実装（`practice.py`本体・`test_practice.py`はステートフルなBank API向けに移植・書き直し済みで単体テストは通る想定だが、実ターミナルでの動作確認は未実施。CLIエントリポイントとして呼べる状態にもなっていない。`stats`相当は未着手）

**依存**: なし。MCPサーバーとは独立しており、`bank.json`というファイル形式だけを介して他ストーリーと関係する

**目的**: MCP接続やAPI呼び出しを一切介さず、生成済みのバンクさえあればローカルで素早く「問題を解く」「成績を見る」を完結できる。通勤中や電波が不安定な環境でも、Claude Code/Desktopを起動していなくても復習を続けられる、という独立した価値。

- [ ] `archforge_mcp/cli.py`（または`__main__.py`）: argparseで`practice`/`stats`の2サブコマンドを用意し、`python -m archforge_mcp <cmd>`で起動できるようにする
- [ ] `practice`サブコマンド: 既存の`run_practice`を`--domain`/`--count`オプション付きで呼び出すだけの薄い配線
- [ ] `stats`サブコマンド（新規実装）: `Bank.domain_stats`の結果を、`config.DOMAINS`の本番重み順（27/18/20/20/15%）に並べて表示する（archforgeの該当ストーリーをそのまま移植する形）
- [ ] 実機で`uv run python -m archforge_mcp practice`を一周動かし、出題・採点・`bank.json`への記録を目視確認する（自動テストは`input()`をmonkeypatchしているだけなので、実ターミナル入出力での確認はまだ済んでいない）
- [ ] 実機で`stats`の表示を確認する

## ストーリー9: Claude Code/DesktopにMCPサーバーとして接続してセットアップできる
状態: 🔲 未着手

**依存**: ストーリー1〜7（接続して意味のあるツール・プロンプトが揃っていること）

**目的**: 初めて使うユーザーが、READMEの手順どおりに進めるだけでClaude CodeまたはClaude DesktopにこのMCPサーバーを接続でき、追加のAPI課金なしで使い始められる。

**DoD**: READMEの手順に従い`uv sync`で環境を整え、Claude Code（`claude mcp add`相当）またはClaude Desktopの設定ファイルにサーバーを登録すると、接続後にツール一覧に`add_questions`/`unattempted`/`record_attempt`/`domain_stats`の4つ、プロンプト一覧に`generate_domain_questions`/`review_questions`/`practice_session`が見える。READMEには「独自コードはAnthropic APIを一切叩かない。生成・レビュー・解説は接続元エージェント（ユーザーのClaude Pro/Maxサブスクリプション）が行う」という設計思想を明記する。

- [ ] `pyproject.toml`に起動コマンドが確定した後、READMEにClaude Code / Claude Desktop両方の接続設定例（`command`/`args`）を記載する
- [ ] README: `uv sync`によるセットアップ手順
- [ ] README: MCPサーバー（生成・保存・成績集計）とオフラインCLI（ストーリー8の`practice`/`stats`）という2つの使い方があることの説明
- [ ] README: archforge同様、「非公式・AI生成の問題バンクである」旨の免責事項
- [ ] 手動確認: Claude Codeから実際に接続し、4ツール+3プロンプトが見えることを確認する

## QA: 動作確認
状態: 🔲 未着手

ストーリーではなく、全ストーリー完了後の最終確認チェックリスト。

- [ ] Claude Codeに接続し、`generate_domain_questions`プロンプトを使って1ドメイン分生成→`add_questions`で保存→`bank.json`の中身を目視確認
- [ ] 同様に`review_questions`プロンプトを使ったレビューを1回試す
- [ ] 会話の中で`practice_session`を使い、出題→誤答→解説→次の問題、を1周確認（追加のAPI課金が発生しないこと＝ユーザー自身のPro/Maxセッション内で完結することを確認）
- [ ] `domain_stats`をチャットで呼び、本番重みと並べた弱点説明が返ることを確認
- [ ] MCP接続を切った状態で`uv run python -m archforge_mcp practice`を実行し、オフラインでも採点ループが動くことを確認
- [ ] `uv run python -m archforge_mcp practice --domain <ドメイン名>`で該当ドメインだけ絞り込み出題されることを確認
- [ ] `uv run python -m archforge_mcp practice --count <N>`で出題数が指定通り制御されることを確認
- [ ] `uv run python -m archforge_mcp stats`の表示を確認
- [ ] `uv run pytest`で既存の`test_bank.py`/`test_practice.py`が実際にこの環境で通ることを確認（移植後まだ実行していない場合はここで初めて確認する）
- [ ] `ruff check .` / `ruff format .`が通ることを確認
