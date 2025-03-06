import { Observable } from 'rxjs';

export abstract class TableColumn<T> {
  key: string;
  label: string;
  getItems: (value: T) => string[];
  getNgClass: (value: T) => string;
  isCopyable: boolean;

  type: string = 'TableColumn';

  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
    isCopyable?: boolean;
  }) {
    this.key = named.key;
    this.label = named.label;
    this.getItems = named.getItems;
    this.getNgClass = named.getNgClass ?? (() => '');
    this.isCopyable = named.isCopyable ?? false;
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
    onClick: (value: T) => void;
    isCopyable?: boolean;
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
    getNgClass: (value: T) => string;
    isCopyable?: boolean;
    routerLink: string;
  }) {
    super(named);
    this.routerLink = named.routerLink;
  }
}
