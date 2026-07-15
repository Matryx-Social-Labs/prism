// design-sync shim: next/link -> plain <a> for the DS bundle.
import * as React from "react";

type Props = React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; prefetch?: boolean };

export default function Link({ href, prefetch: _prefetch, children, ...rest }: Props) {
  return (
    <a href={href} {...rest}>
      {children}
    </a>
  );
}
