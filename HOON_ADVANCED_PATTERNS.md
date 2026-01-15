# HOON ADVANCED PATTERNS & EXAMPLES — LLM SUPPLEMENT

## PARSING PATTERNS

### Basic Parser Combinators

Hoon uses parser combinators via `;~` (micsig):

```hoon
:: Parse a single character
(scan "a" (just 'a'))  :: 'a'

:: Parse alternatives
(scan "a" ;~(pose (just 'a') (just 'b')))  :: 'a'

:: Parse sequence (keep all)
(scan "ab" ;~(plug (just 'a') (just 'b')))  :: ['a' 'b']

:: Parse sequence (keep first/second)
(scan "ab" ;~(sfix (just 'a') (just 'b')))  :: 'a' (drop second)
(scan "ab" ;~(pfix (just 'a') (just 'b')))  :: 'b' (drop first)

:: Glue with separator
(scan "a,b,c" (more com alf))  :: ['a' 'b' 'c' ~]
```

### Common Parsers

```hoon
:: Digits and numbers
dem    :: Parse decimal number
hex    :: Parse hex number
dim    :: Parse decimal with dots

:: Text
alf    :: Single lowercase letter
aln    :: Alphanumeric
alp    :: Alphanumeric + hyphen
qit    :: Any printable except "
```

### Parser Example: CSV Line

```hoon
|=  line=tape
^-  (list tape)
%+  scan  line
%+  more  com
(star ;~(less com prn))
```

## GATE PATTERNS

### Currying with Doors

```hoon
:: Create a curried adder
|_  base=@
++  add-to
  |=  n=@
  (add base n)
--

:: Usage
=/  add-five  ~(add-to door 5)
(add-five 10)  :: 15
```

### Wet Gates (Generics)

```hoon
:: Generic identity
|*  a=*
a

:: Generic pair maker
|*  [a=* b=*]
[a b]

:: The turn function (map over list)
++  turn
  |*  [a=(list) b=gate]
  ^-  (list _?>(?=(^ a) (b i.a)))
  ?~  a  ~
  [i=(b i.a) t=$(a t.a)]
```

### Gate Builders

```hoon
:: Function that returns a gate
++  make-adder
  |=  n=@
  |=  m=@
  (add n m)

:: Usage
=/  add-ten  (make-adder 10)
(add-ten 5)  :: 15
```

## RECURSION PATTERNS

### Accumulator Pattern

```hoon
:: Factorial with accumulator
|=  n=@
=/  acc  1
|-
?:  (lte n 1)  acc
$(n (dec n), acc (mul n acc))
```

### Mutual Recursion

```hoon
|%
++  even
  |=  n=@
  ?:  =(n 0)  %.y
  (odd (dec n))
++  odd
  |=  n=@
  ?:  =(n 0)  %.n
  (even (dec n))
--
```

### Tree Traversal

```hoon
:: Sum all atoms in a noun
|=  n=*
^-  @
?@  n  n                      :: If atom, return it
(add $(n -.n) $(n +.n))       :: Else recurse on head and tail
```

## STATE PATTERNS

### State Threading with =^

```hoon
:: Generate multiple random numbers
=/  rng  ~(. og eny)
=^  n1  rng  (rads:rng 100)
=^  n2  rng  (rads:rng 100)
=^  n3  rng  (rads:rng 100)
[n1 n2 n3]
```

### The `=^` Pattern in Agents

```hoon
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card _this)
  =^  cards  state  (handle-poke mark vase)
  [cards this]
::
++  handle-poke
  |=  [=mark =vase]
  ^-  (quip card _state)
  :: ... returns [cards new-state]
```

## COMMON DATA STRUCTURES

### Working with Maps

```hoon
:: Create map
=/  m  (my ~[[%foo 1] [%bar 2]])

:: Insert/update
=.  m  (~(put by m) %baz 3)

:: Lookup patterns
=/  val  (~(get by m) %foo)   :: (unit @)
?~  val  
  ~|  'key not found'  !!
u.val                          :: Unwrap unit

:: Or use got (crashes if missing)
(~(got by m) %foo)             :: @ directly

:: Transform all values
(~(run by m) |=(v=@ (mul v 2)))

:: Get all keys or values
~(key by m)  :: (set key)
~(val by m)  :: (list value)
```

### Working with Sets

```hoon
:: Create set
=/  s  (sy ~[1 2 3])

:: Operations
=.  s  (~(put in s) 4)         :: Add
=.  s  (~(del in s) 1)         :: Remove
(~(has in s) 2)                :: Check membership

:: Set operations
(~(int in s) other-set)        :: Intersection
(~(uni in s) other-set)        :: Union
(~(dif in s) other-set)        :: Difference
```

### Working with Lists

```hoon
:: Build list efficiently (cons to head, flop at end)
=|  acc=(list @)
|-
?~  input  (flop acc)
$(input t.input, acc [processed-i.input acc])

:: Index access
(snag 2 my-list)               :: Get index 2
(snap my-list 2 new-val)       :: Set index 2

:: Find in list
(find ~[target] my-list)       :: (unit @) - index

:: List of lists
(zing list-of-lists)           :: Flatten one level
```

## AGENT PATTERNS

### Subscription Management

```hoon
:: Watch a path
[%pass /wire %agent [target %agent-name] %watch /path]

:: Handle subscription
++  on-watch
  |=  =path
  ^-  (quip card _this)
  ?+  path  (on-watch:def path)
    [%updates ~]  `this
    [%updates @ ~]  
      =/  id  i.t.path
      :: validate, maybe send initial state
      `this
  ==

:: Send updates to subscribers
[%give %fact ~[/path] %mark !>(data)]

:: Send to specific subscriber wire
[%give %fact ~  %mark !>(data)]  :: To requester only
```

### Poke Patterns

```hoon
:: Send poke
[%pass /wire %agent [target %agent-name] %poke %action !>(my-action)]

:: Handle incoming poke
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card _this)
  ?>  =(src.bowl our.bowl)     :: Require local
  ?+  mark  (on-poke:def mark vase)
    %noun      `this           :: Accept any
    %action
      =/  act  !<(action vase)
      (handle-action act)
  ==
```

### Timer Pattern

```hoon
:: Set timer
[%pass /timer %arvo %b %wait (add now.bowl ~m5)]

:: Handle timer
++  on-arvo
  |=  [=wire =sign-arvo]
  ^-  (quip card _this)
  ?+  wire  (on-arvo:def wire sign-arvo)
    [%timer ~]
      ?>  ?=([%behn %wake *] sign-arvo)
      ?^  error.sign-arvo
        :: Handle error
        `this
      :: Timer fired, do work
      :_  this
      ~[[%pass /timer %arvo %b %wait (add now.bowl ~m5)]]
  ==
```

## TEXT HANDLING

### Cord vs Tape

```hoon
:: Cord (@t): atom, efficient storage
'hello world'

:: Tape: (list @t), easy manipulation
"hello world"

:: Convert
(trip 'cord')    :: "cord"
(crip "tape")    :: 'tape'
```

### String Building

```hoon
:: Tape interpolation
"{<some-value>} in tape"

:: Building complex strings
=/  parts=(list tape)  ~["hello" " " "world"]
(zing parts)  :: "hello world"

:: Number to text
(scow %ud 1.234)       :: "1.234"
(scow %ux 0xdead)      :: "0xdead"

:: Text to number
(slaw %ud '1.234')     :: [~ 1.234]
(slav %ud '1.234')     :: 1.234 (crash on fail)
```

### Tank Formatting

```hoon
:: Print for debugging
~&  >  'loud message'      :: Red
~&  >>  'louder'           :: Brighter
~&  >>>  'loudest'         :: Brightest

:: Structured output
~&  [%key value %other other]
body

:: Tank types
leaf+"simple text"         
[%rose [" " "(" ")"] ~[leaf+"a" leaf+"b"]]  :: (a b)
[%palm [" " "{" "." "}"] ~[leaf+"a"]]       :: {.a }
```

## JSON HANDLING

### JSON Types

```hoon
:: $json in /sur/json.hoon
$%  [%a p=(list json)]     :: Array
    [%b p=?]               :: Boolean  
    [%n p=@ta]             :: Number (as text)
    [%o p=(map @t json)]   :: Object
    [%s p=@t]              :: String
    ~                      :: Null
==
```

### Encoding (Hoon → JSON)

```hoon
:: Use enjs:format
=,  enjs:format
%-  pairs
:~  ['name' s+'John']
    ['age' (numb 30)]
    ['active' b+%.y]
    ['tags' a+~[s+'a' s+'b']]
==
```

### Decoding (JSON → Hoon)

```hoon
:: Use dejs:format
=,  dejs:format
^-  [name=@t age=@ud]
%.  json-value
%-  ot
:~  [%name so]             :: String → @t
    [%age ni]              :: Number → @ud
==
```

### Mark File for JSON

```hoon
::  /mar/my-action.hoon
/-  *my-sur
|_  act=action
++  grab
  |%
  ++  noun  action
  ++  json  
    =,  dejs:format
    |=  jon=json
    ^-  action
    %.  jon
    %-  of
    :~  [%add (ot ~[[%item so]])]
        [%del (ot ~[[%id ni]])]
    ==
  --
++  grow
  |%
  ++  noun  act
  ++  json
    =,  enjs:format
    ?-  -.act
      %add  (pairs ~[['item' s+item.act]])
      %del  (pairs ~[['id' (numb id.act)]])
    ==
  --
++  grad  %noun
--
```

## SCRY PATTERNS

### Local Scry

```hoon
:: Scry syntax: .^(type %vane /path)
.^(@ %cx /=desk=/gen/code/hoon)  :: Read file
.^((list path) %ct /=desk=/)     :: List directory
.^(ship %j /=our=)               :: Get our ship

:: Agent scry (via on-peek)
.^(json %gx /=agent=/path/json)
```

### Implementing on-peek

```hoon
++  on-peek
  |=  =path
  ^-  (unit (unit cage))
  ?+  path  [~ ~]
    [%x %state ~]     ``noun+!>(state)
    [%x %item @ ~]
      =/  id  (slav %ud i.t.t.path)
      =/  item  (~(get by items.state) id)
      ?~  item  [~ ~]
      ``noun+!>(u.item)
  ==
```

## THREAD PATTERNS

### Basic Thread

```hoon
::  /ted/my-thread.hoon
/-  spider
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  m  (strand ,vase)
^-  form:m
;<  =bowl:spider  bind:m  get-bowl:strandio
;<  ~  bind:m  (poke [our.bowl %agent] %noun !>(~))
(pure:m !>('done'))
```

### Thread with HTTP

```hoon
;<  =caged-cage  bind:m
  %-  fetch-json:strandio
  'https://api.example.com/data'
=/  =json  !<(json q.caged-cage)
:: Process json...
```

## COMMON GOTCHAS

### Face Shadowing

```hoon
:: WRONG: shadows outer 'a'
=/  a  5
=/  a  10    :: Now 'a' is 10, old 'a' inaccessible

:: RIGHT: use different names
=/  a  5
=/  b  10
```

### Unit Unwrapping

```hoon
:: WRONG: accessing u without checking
=/  val  (~(get by map) key)
u.val    :: Crashes if val is ~

:: RIGHT: always check
?~  val  default
u.val

:: Or use (need val) for intentional crash
```

### List vs Null-Terminated Tuple

```hoon
:: These are different types!
`(list @)`~[1 2 3]    :: Explicit list
~[1 2 3]              :: Could be [1 2 3 ~] tuple

:: Always cast when type matters
`(list @)`~[1 2 3]
```

### Gate vs Arm

```hoon
:: Arm: computed on reference
++  my-arm  (some-computation)  :: Runs each time

:: Gate: value with sample
++  my-gate  
  |=  x=@
  (some-computation x)          :: Runs when called
```

### Equality vs Nest

```hoon
:: = tests value equality (Nock 5)
=(~[1 2] ~[1 2])     :: %.y

:: But types may differ!
=/  a  `(list @ud)`~[1 2]
=/  b  `(list @)`~[1 2]
=(a b)               :: %.y (values equal)
:: But (list @ud) nests in (list @), not vice versa
```

## PERFORMANCE TIPS

1. **Avoid repeated map lookups** - store result in face
2. **Build lists with cons + flop** - O(n) vs O(n²)
3. **Use `++got:by` over `++get:by` + unwrap** when crash is acceptable
4. **Prefer cords over tapes for storage** - atoms are smaller
5. **Use `++weld` sparingly** - O(n) in first list length
6. **Profile with `~&  %spot  expr`** - prints timing

---

*This supplement accompanies HOON_LLM_HEADER.md*
