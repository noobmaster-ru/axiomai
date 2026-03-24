import type { ReactNode } from "react";
import "./InstructionContent.css";

type InstructionContentProps = {
  className?: string;
  text: string;
};

type InlinePart = {
  type: "text" | "strong";
  value: string;
};

type ParagraphBlock = {
  lines: InlinePart[][];
  type: "paragraph";
};

type ListBlock = {
  items: InlinePart[][];
  type: "ol" | "ul";
};

type ContentBlock = ParagraphBlock | ListBlock;

function joinClassNames(...classNames: Array<string | undefined>) {
  return classNames.filter(Boolean).join(" ");
}

function parseInline(value: string): InlinePart[] {
  const parts: InlinePart[] = [];
  const pattern = /\*([^*\n]+)\*/g;
  let lastIndex = 0;

  for (const match of value.matchAll(pattern)) {
    const matchIndex = match.index ?? 0;

    if (matchIndex > lastIndex) {
      parts.push({
        type: "text",
        value: value.slice(lastIndex, matchIndex),
      });
    }

    parts.push({
      type: "strong",
      value: match[1],
    });

    lastIndex = matchIndex + match[0].length;
  }

  if (lastIndex < value.length) {
    parts.push({
      type: "text",
      value: value.slice(lastIndex),
    });
  }

  return parts.length ? parts : [{ type: "text", value }];
}

function parseBlocks(text: string): ContentBlock[] {
  const normalizedText = text
    .replace(/\r\n?/g, "\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .trim();

  if (!normalizedText) {
    return [];
  }

  const blocks: ContentBlock[] = [];
  const lines = normalizedText.split("\n");
  let currentParagraph: string[] = [];
  let currentList: { items: string[]; type: "ol" | "ul" } | null = null;

  function flushParagraph() {
    if (!currentParagraph.length) {
      return;
    }

    blocks.push({
      type: "paragraph",
      lines: currentParagraph.map((line) => parseInline(line)),
    });
    currentParagraph = [];
  }

  function flushList() {
    if (!currentList || !currentList.items.length) {
      currentList = null;
      return;
    }

    blocks.push({
      type: currentList.type,
      items: currentList.items.map((item) => parseInline(item)),
    });
    currentList = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const bulletMatch = line.match(/^[-•]\s+(.+)$/);
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);

    if (bulletMatch || orderedMatch) {
      flushParagraph();

      const nextType = orderedMatch ? "ol" : "ul";
      const nextValue = (orderedMatch?.[1] ?? bulletMatch?.[1] ?? "").trim();

      if (!currentList || currentList.type !== nextType) {
        flushList();
        currentList = {
          type: nextType,
          items: [],
        };
      }

      currentList.items.push(nextValue);
      continue;
    }

    flushList();
    currentParagraph.push(line);
  }

  flushParagraph();
  flushList();

  return blocks;
}

function renderInline(parts: InlinePart[], keyPrefix: string): ReactNode {
  return parts.map((part, index) => {
    if (part.type === "strong") {
      return (
        <strong className="instruction-content__strong" key={`${keyPrefix}-strong-${index}`}>
          {part.value}
        </strong>
      );
    }

    return <span key={`${keyPrefix}-text-${index}`}>{part.value}</span>;
  });
}

export function InstructionContent({ className, text }: InstructionContentProps) {
  const blocks = parseBlocks(text);

  if (!blocks.length) {
    return null;
  }

  return (
    <div className={joinClassNames("instruction-content", className)}>
      {blocks.map((block, blockIndex) => {
        if (block.type === "paragraph") {
          return (
            <p className="instruction-content__paragraph" key={`paragraph-${blockIndex}`}>
              {block.lines.map((line, lineIndex) => (
                <span className="instruction-content__line" key={`paragraph-${blockIndex}-line-${lineIndex}`}>
                  {lineIndex > 0 ? <br /> : null}
                  {renderInline(line, `paragraph-${blockIndex}-line-${lineIndex}`)}
                </span>
              ))}
            </p>
          );
        }

        const ListTag = block.type;

        return (
          <ListTag className="instruction-content__list" key={`list-${blockIndex}`}>
            {block.items.map((item, itemIndex) => (
              <li className="instruction-content__item" key={`list-${blockIndex}-item-${itemIndex}`}>
                {renderInline(item, `list-${blockIndex}-item-${itemIndex}`)}
              </li>
            ))}
          </ListTag>
        );
      })}
    </div>
  );
}
