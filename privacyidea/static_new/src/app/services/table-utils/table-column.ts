import { Observable } from 'rxjs';

export abstract class TableColumn<T> {
  key: string;
  label: string;
  getItems: (value: T) => string[];
  getNgClass: (value: T) => string;
  isCopyable: boolean;
  align:
    | 'start'
    | 'end'
    | 'left'
    | 'right'
    | 'center'
    | 'justify'
    | 'match-parent';
  type: string = 'TableColumn';

  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
    isCopyable?: boolean;
    align?:
      | 'start'
      | 'end'
      | 'left'
      | 'right'
      | 'center'
      | 'justify'
      | 'match-parent';
  }) {
    this.key = named.key;
    this.label = named.label;
    this.getItems = named.getItems;
    this.getNgClass = named.getNgClass ?? (() => '');
    this.isCopyable = named.isCopyable ?? false;
    this.align = named.align ?? 'left';
  }
}

export class SimpleTableColumn<T> extends TableColumn<T> {
  override type: string = 'SimpleTableColumn';
  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
    isCopyable?: boolean;
    align?:
      | 'start'
      | 'end'
      | 'left'
      | 'right'
      | 'center'
      | 'justify'
      | 'match-parent';
  }) {
    super(named);
  }
}

export class OnClickTableColumn<T> extends TableColumn<T> {
  override type: string = 'OnClickTableColumn';
  onClick: (value: T) => Observable<any> | void = () => {};
  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
    onClick: (value: T) => Observable<any> | void;
    isCopyable?: boolean;
    align?:
      | 'start'
      | 'end'
      | 'left'
      | 'right'
      | 'center'
      | 'justify'
      | 'match-parent';
  }) {
    super(named);
    this.onClick = named.onClick;
  }
}

export class RouterTableColumn<T> extends TableColumn<T> {
  override type: string = 'RouterTableColumn';
  routerLink: string;
  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
    isCopyable?: boolean;
    routerLink: string;
    align?:
      | 'start'
      | 'end'
      | 'left'
      | 'right'
      | 'center'
      | 'justify'
      | 'match-parent';
  }) {
    super(named);
    this.routerLink = named.routerLink;
  }
}
