import { Observable } from 'rxjs';

export abstract class TableColumn<T> {
  key: string;
  label: string;
  getItems: (value: T) => string[];
  getNgClass: (value: T) => string;
  type: string = 'TableColumn';

  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
  }) {
    this.key = named.key;
    this.label = named.label;
    this.getItems = named.getItems;
    this.getNgClass = named.getNgClass ?? (() => '');
  }

  isSimpleColumn(): boolean {
    return this instanceof SimpleTableColumn;
  }

  isOnClickColumn(): boolean {
    return this instanceof OnClickTableColumn;
  }

  isRouterColumn(): boolean {
    return this instanceof RouterTableColumn;
  }
}

export class SimpleTableColumn<T> extends TableColumn<T> {
  override type: string = 'SimpleTableColumn';
  constructor(named: {
    key: string;
    label: string;
    getItems: (value: T) => string[];
    getNgClass?: (value: T) => string;
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
    routerLink: string;
  }) {
    super(named);
    this.routerLink = named.routerLink;
  }
}
