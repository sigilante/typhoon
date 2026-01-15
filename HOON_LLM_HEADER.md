# HOON PROGRAMMING LANGUAGE — LLM REFERENCE

You are an expert Hoon programmer. Hoon is a statically typed, purely functional, strictly evaluated language that compiles to Nock. All Urbit software is written in Hoon.

## FUNDAMENTAL CONCEPTS

### Nouns: The Only Data Type

Everything in Hoon is a **noun**:
- **Atom**: Any unsigned integer (arbitrary precision)
- **Cell**: An ordered pair of nouns `[a b]`

Cells nest rightward: `[a b c]` = `[a [b c]]`

### The Subject

Hoon is **subject-oriented**. Every expression evaluates against a **subject** (the context/environment). The subject is:
- The lexical scope
- The data environment  
- The implicit argument to every computation

The `.` dot refers to the current subject.

### Runes

Runes are two-character ASCII digraphs that define expression syntax (like keywords). Runes take a fixed number of children, separated by `gap` (2+ spaces or newline).

**Whitespace rules:**
- `ace` = single space (within expressions)
- `gap` = two+ spaces OR newline (between children)

### Rune Families

| Glyph | Name | Purpose |
|-------|------|---------|
| `\|` | bar | Create cores |
| `$` | buc | Define structures/molds |
| `%` | cen | Function calls |
| `:` | col | Create cells |
| `.` | dot | Nock operations |
| `/` | fas | File imports |
| `^` | ket | Type casts |
| `+` | lus | Define arms |
| `;` | mic | Macros, composition |
| `~` | sig | Hints (non-semantic) |
| `=` | tis | Subject modification |
| `?` | wut | Conditionals |
| `!` | zap | Special/wild |

## CORE RUNES (ESSENTIAL)

### Subject Modification (`=` tis)

```hoon
=/  name  value  body    :: Pin face to subject ("let binding")
=.  wing  value  body    :: Modify existing wing
=^  p  q  r  s           :: Pin p from head of r, put tail in q
=>  p  q                 :: Evaluate q with p as subject  
=<  p  q                 :: Evaluate p with q as subject (inverted =>)
=*  name  expr  body     :: Create alias (deferred expression)
=|  spec  body           :: Pin bunt (default value) to subject
```

**Prefer `=/` over `=+` or `=-`** for clarity.

### Cores (`|` bar)

```hoon
|%                       :: Multi-arm core
++  arm-name  expr       :: Arm definition
--                       :: Close core

|=  sample  body         :: Gate (function): core with $ arm and sample
|-  body                 :: Trap: core with $ arm, evaluate immediately
|.  body                 :: Trap: core with $ arm, don't evaluate
|^  body  ++arms  --     :: Cork: multi-arm core, evaluate $ immediately
|_  sample  ++arms  --   :: Door: core with sample (object-like)
|*  sample  body         :: Wet gate (generic/polymorphic)
```

**Core = `[battery payload]`**
- Battery: compiled Nock code (arms)
- Payload: data context

**Gate = core with `$` arm and sample**

### Function Calls (`%` cen)

```hoon
%-  gate  arg            :: Call gate with one argument
%+  gate  arg1  arg2     :: Call gate with two arguments
%:  gate  arg1  arg2 ... :: Call gate with n arguments
%~  arm  door  arg       :: Pull arm from door with sample
%=  wing  a  b  c  d  ==  :: Resolve wing with changes (recursion)
```

**Irregular forms:**
- `(gate arg)` = `%-  gate  arg`
- `(gate a b)` = `%+  gate  a  b`
- `~(arm door arg)` = `%~  arm  door  arg`

### Conditionals (`?` wut)

```hoon
?:  cond  if-yes  if-no  :: Branch on loobean
?.  cond  if-no  if-yes  :: Inverted ?: (heavy branch lower)
?~  val  if-null  else   :: Branch on null
?-  val                  :: Switch on type (exhaustive)
  %foo  expr-foo
  %bar  expr-bar
==
?+  val  default         :: Switch with default
  %foo  expr-foo
==
?=  spec  val            :: Type test (for inference)
?>  cond  body           :: Assert true or crash
?<  cond  body           :: Assert false or crash
?@  val  if-atom  if-cell  :: Branch atom/cell
?^  val  if-cell  if-atom  :: Branch cell/atom
```

**Loobeans:** `%.y` (yes/true = 0), `%.n` (no/false = 1)

**Irregular:** `=(a b)` = `.=  a  b` (equality test)

### Cells (`:` col)

```hoon
:-  a  b                 :: Cell [a b]
:+  a  b  c              :: Triple [a b c]
:^  a  b  c  d           :: Quad [a b c d]
:~  a  b  c  ==          :: Null-terminated list [a b c ~]
:*  a  b  c  ==          :: Tuple [a b c]
```

**Irregular:** `[a b c]` = `:*  a  b  c  ==`

### Type Casts (`^` ket)

```hoon
^-  type  expr           :: Cast to type (nest-fail if incompatible)
^+  sample  expr         :: Cast to type of sample
^*  type                 :: Bunt: default value of type
^=  face  expr           :: Apply face (name)
```

**Irregular:**
- `` `type`expr `` = `^-  type  expr`
- `face=expr` = `^=  face  expr`
- `*type` = `^*  type`

### Hints (`~` sig)

```hoon
~&  expr  body           :: Printf debugging (print expr)
~|  expr  body           :: Crash annotation (print on failure)
~_  tank  body           :: User-formatted crash message
```

## AURAS (Atom Types)

Auras are soft type tags for atoms. They nest hierarchically.

| Aura | Meaning | Example |
|------|---------|---------|
| `@` | Any atom | `42` |
| `@ud` | Unsigned decimal | `1.000` (thousands separator: `.`) |
| `@ux` | Hexadecimal | `0xdead.beef` |
| `@ub` | Binary | `0b1010` |
| `@t` | UTF-8 cord | `'hello'` |
| `@ta` | URL-safe ASCII (knot) | `~.foo-bar` |
| `@tas` | Symbol (term) | `%foo` |
| `@p` | Ship name | `~zod`, `~sampel-palnet` |
| `@da` | Absolute datetime | `~2024.1.1` |
| `@dr` | Relative time | `~h1.m30` |
| `@rs` | Single-precision float | `.3.14` |
| `@rd` | Double-precision float | `.~3.14159` |
| `@s` | Signed integer | `--5` (neg), `-5` (pos) |

**Bitwidth suffix:** Capital letter = 2^n bits (D=8, E=16, F=32, G=64)

## MOLDS (Type Definitions)

Molds are functions that validate/normalize nouns.

```hoon
+$  name  type           :: Define named mold

:: Built-in mold builders:
$:  [a=@ b=@]            :: Tuple mold
$%  [%foo a=@]           :: Tagged union
    [%bar b=@]
==
$?  %foo  %bar           :: Type union (atoms only)
$@  atom-type  cell-type :: Union of atom and cell type
$_  example              :: Mold from example value
(list @ud)               :: Parameterized mold
(map @tas @ud)           :: Map type
(set @ud)                :: Set type
(unit @ud)               :: Optional (~ or [~ u=val])
```

**Irregular:** `?(%foo %bar)` = `$?  %foo  %bar`

## COMMON PATTERNS

### Gate Definition
```hoon
|=  [a=@ b=@]            :: Sample spec
^-  @                    :: Return type
(add a b)                :: Body
```

### Recursion
```hoon
|-                       :: Create trap
?:  (lte n 1)  1         :: Base case
(mul n $(n (dec n)))     :: Recurse: $() calls $ arm with changes
```

### List Processing
```hoon
:: Iterate with turn (map)
(turn my-list |=(x=@ (mul x 2)))

:: Filter with skim/skip
(skim my-list |=(x=@ (gth x 5)))

:: Fold with roll (left) or reel (right)
(roll my-list add)

:: Recursive list processing
=|  acc=(list @)
|-
?~  items  (flop acc)    :: ?~ branches on null
$(items t.items, acc [i.items acc])
```

### Map/Set Operations
```hoon
:: Map operations via +by door
(~(put by my-map) key value)   :: Insert
(~(get by my-map) key)         :: Lookup -> (unit value)
(~(got by my-map) key)         :: Lookup -> value (crash if missing)
(~(has by my-map) key)         :: Check membership -> ?
(~(del by my-map) key)         :: Delete

:: Set operations via +in door
(~(put in my-set) elem)
(~(has in my-set) elem)
(~(del in my-set) elem)
```

### Unit Handling
```hoon
?~  maybe-val             :: Branch on unit
  default-val             :: ~ case
thing-to-do-with-u.maybe-val  :: [~ u=x] case, .u is now in scope
```

### Core with Helper Arms
```hoon
|^
::  Main expression ($ arm)
(helper-one (helper-two x))
::
++  helper-one
  |=  a=@  (add a 1)
++  helper-two  
  |=  a=@  (mul a 2)
--
```

## GALL AGENT STRUCTURE

Agents are doors with exactly 10 arms:

```hoon
|_  =bowl:gall
++  on-init    :: -> (quip card _this)   :: First start
++  on-save    :: -> vase                 :: Export state
++  on-load    :: vase -> (quip card _this)  :: Import state
++  on-poke    :: cage -> (quip card _this)  :: Handle poke
++  on-watch   :: path -> (quip card _this)  :: Subscribe request
++  on-leave   :: path -> (quip card _this)  :: Unsubscribe
++  on-peek    :: path -> (unit (unit cage)) :: Scry
++  on-agent   :: [wire sign:agent:gall] -> (quip card _this)
++  on-arvo    :: [wire sign-arvo] -> (quip card _this)
++  on-fail    :: [term tang] -> (quip card _this)
--
```

**Return type:** Most arms return `(quip card _this)` = `[(list card) agent]`

### Agent Boilerplate
```hoon
/-  *our-sur              :: Import /sur file
/+  *our-lib, default-agent  :: Import /lib files
|%
+$  versioned-state
  $%  [%0 state-0]
  ==
+$  state-0  [field=@ud]
+$  card  card:agent:gall
--
%-  agent:dbug
=|  state-0
=*  state  -
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def   ~(. (default-agent this %.n) bowl)
++  on-init
  ^-  (quip card _this)
  `this
:: ... other arms
--
```

## THE ENGINE PATTERN (++abet)

For complex state management, use nested cores:

```hoon
|_  [=bowl:gall cards=(list card)]
++  abet  [(flop cards) state]  :: Finalize: return cards + state
++  cor   .                      :: Self-reference
++  emit  |=(=card cor(cards [card cards]))  :: Add card
++  emil  |=(caz=(list card) cor(cards (welp (flop caz) cards)))
::
++  handle-action
  |=  =action
  ^+  cor
  ?-  -.action
    %foo  (emit [%pass /wire %agent ...])
    %bar  cor  :: no-op
  ==
--
```

**Usage:** `abet:(handle-action:cor action)`

## COMMON STANDARD LIBRARY

### Arithmetic
`add`, `sub`, `mul`, `div`, `mod`, `pow`, `gth`, `lth`, `gte`, `lte`

### List Operations
`lent` (length), `snag` (index), `snap` (update at index), `turn` (map), `roll`/`reel` (fold), `skim`/`skip` (filter), `weld` (concat), `flop` (reverse), `sort`, `gulf` (range)

### Text
- `trip`: cord -> tape
- `crip`: tape -> cord
- `scot`: atom -> knot (format)
- `slaw`: knot -> (unit atom) (parse)

### Tree Navigation (Lark Notation)
- `-` = head, `+` = tail
- `-<` = head of head, `->` = tail of head
- `+<` = head of tail, `+>` = tail of tail

## STYLE GUIDELINES

1. **Tall form preferred** for readability; wide form for short expressions
2. **80 columns max**, prefer 56 for docs
3. **Heavy branch lower**: Use `?.` when true-branch is heavier
4. **Comments**: `::` for line comments
5. **Naming**: Lowercase with hyphens (`my-gate`), short names for local bindings
6. **Arms**: Prefix with `+` when referencing (`+add`), `$` for molds (`$tape`)
7. **Faces**: Use `.face` for values, avoid shadowing

### Formatting Example
```hoon
::  Good: Tall form, aligned children
=/  x  5
=/  y  10
?:  (gth x y)
  x
(add x y)

::  Good: Short expression in wide form
(add 2 2)

::  Avoid: Mixing forms inconsistently
```

## COMMON ERRORS

| Error | Meaning |
|-------|---------|
| `mint-nice` | Type mismatch |
| `mint-vain` | Unreachable branch |
| `nest-fail` | Cast failed |
| `-find.foo` | Name not in subject |
| `fish-loop` | Recursive type checking |
| `generator-build-fail` | Syntax/compile error |

## DEBUGGING

```hoon
!:                       :: Enable stack traces (top of file)
~&  value  rest          :: Print value, continue
~|  value  rest          :: Print value on crash
!>  value                :: Create vase (inspect type+value)
;;  type  value          :: Normalize (crash if doesn't fit)
```

## IMPORTS (Ford Runes)

```hoon
/-  sur-file             :: Import /sur
/+  lib-file             :: Import /lib  
/=  face  /path          :: Import with face
/*  face  %mark  /path   :: Import file as mark
```

## KEY IRREGULAR FORMS SUMMARY

| Irregular | Regular | Purpose |
|-----------|---------|---------|
| `[a b c]` | `:*  a  b  c  ==` | Cell/tuple |
| `(gate arg)` | `%-  gate  arg` | Call gate |
| `~(arm door arg)` | `%~  arm  door  arg` | Pull arm |
| `` `type`val `` | `^-  type  val` | Cast |
| `face=val` | `^=  face  val` | Apply face |
| `*type` | `^*  type` | Bunt |
| `_val` | `$_  val` | Mold from example |
| `=(a b)` | `.=  a  b` | Equality |
| `+(n)` | `.+  n` | Increment |
| `!` | `?!` | NOT |
| `&(a b)` | `?&  a  b  ==` | AND |
| `\|(a b)` | `?\|  a  b  ==` | OR |
| `?(%a %b)` | `$?  %a  %b  ==` | Type union |

## FILE ORGANIZATION

```
/app/agent-name.hoon     :: Gall agent
/sur/agent-name.hoon     :: Structures (one per agent)
/lib/agent-name.hoon     :: Library (one per agent)
/lib/agent-name/json.hoon :: JSON handling
/mar/agent-name/action.hoon :: Mark files
/gen/generator.hoon      :: Generators
/ted/thread.hoon         :: Threads
/tests/agent-name/tests.hoon :: Tests
```

---

*Reference: https://docs.urbit.org*
