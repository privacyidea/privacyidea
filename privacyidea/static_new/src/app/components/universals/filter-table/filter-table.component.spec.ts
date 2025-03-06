import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FilterTable } from './filter-table.component';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { PageEvent } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { OnClickTableColumn } from '../../../services/table-utils/table-column';
import { KeywordFilter } from '../../../services/keyword_filter';
import {
  provideHttpClient,
  withInterceptorsFromDi,
} from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
describe('FilterTable', () => {
  let component: FilterTable<any>;
  let fixture: ComponentFixture<FilterTable<any>>;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FilterTable, BrowserAnimationsModule],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            serial_list: ['Mock serial'],
          },
        },
        provideHttpClient(withInterceptorsFromDi()),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(FilterTable);
    component = fixture.componentInstance;
    component.basicFilters = [];
    component.columns = [];
    component.fetchDataHandler = jasmine.createSpy();
    component.processDataSource = jasmine.createSpy();
    fixture.detectChanges();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });
  describe('handleFilterInput', () => {
    it('should update filterValue and fetch data on input event', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      const inputEvent = new Event('input');
      const inputElement = document.createElement('input');
      inputElement.value = 'test filter';
      component.filterValue = inputElement.value;
      inputElement.dispatchEvent(inputEvent);
      component.handleFilterInput(inputEvent);
      expect(component.filterValue).toBe('test filter');
      expect(component.pageIndex).toBe(0);
      expect(fetchDataSpy).toHaveBeenCalled();
    });
    it('should log an error for unexpected event target', () => {
      const consoleErrorSpy = spyOn(console, 'error');
      spyOn(component, 'fetchData').and.returnValue(undefined);
      const divElement = document.createElement('div');
      const inputEvent = new Event('input', {
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(inputEvent, 'target', { value: divElement });
      component.handleFilterInput(inputEvent);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Unexpected event target:',
        divElement,
      );
    });
  });
  describe('handlePageEvent', () => {
    it('should update pageSize and pageIndex, and fetch data', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      const pageEvent: PageEvent = {
        pageIndex: 1,
        pageSize: 25,
        length: 100,
      };
      component.handlePageEvent(pageEvent);
      expect(component.pageSize).toBe(25);
      expect(component.pageIndex).toBe(1);
      expect(fetchDataSpy).toHaveBeenCalled();
    });
    it('should reset pageIndex to 0 if pageSize changes', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      component.pageIndex = 2;
      const pageEvent: PageEvent = {
        pageIndex: 1,
        pageSize: 50,
        length: 100,
      };
      component.handlePageEvent(pageEvent);
      expect(component.pageSize).toBe(50);
      expect(component.pageIndex).toBe(1);
      expect(fetchDataSpy).toHaveBeenCalled();
    });
  });
  describe('handleSortEvent', () => {
    it('should update sortby_sortdir and fetch data', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      component.sort = {
        active: 'name',
        direction: 'asc',
      } as MatSort;
      component.handleSortEvent();
      expect(component.sortby_sortdir).toEqual({
        active: 'name',
        direction: 'asc',
      });
      expect(component.pageIndex).toBe(0);
      expect(fetchDataSpy).toHaveBeenCalled();
    });
    it('should set sortby_sortdir to undefined if sort is not defined', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      component.sort = undefined!;
      component.handleSortEvent();
      expect(component.sortby_sortdir).toBeUndefined();
      expect(component.pageIndex).toBe(0);
      expect(fetchDataSpy).toHaveBeenCalled();
    });
  });
  describe('handleOnClick', () => {
    it('should call onClick when handleOnClick is called', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      const onClickSpy = jasmine.createSpy().and.returnValue({
        subscribe: (callback: any) => {
          if (typeof callback === 'function') callback();
        },
      });
      const column = new OnClickTableColumn({
        key: 'name',
        label: 'Name',
        getItems: (element: any) => [element.name],
        onClick: onClickSpy,
      });
      const element = { name: 'test' };
      component.handleOnClick(element, column);
      expect(onClickSpy).toHaveBeenCalledWith(element);
    });
  });
  describe('toggleKeyword', () => {
    it('should toggle keyword and fetch data', () => {
      const fetchDataSpy = spyOn(component, 'fetchData');
      const keywordFilter: KeywordFilter = {
        keyword: 'test',
        label: 'Test Label',
        isSelected: () => false,
        getIconName: () => 'icon',
        toggleKeyword: jasmine
          .createSpy('toggleKeyword')
          .and.callFake((currentValue: string) => {
            return `${currentValue} newFilter: filterValue2`;
          }),
      };
      const htmlElement = document.createElement('div');
      spyOn(htmlElement, 'focus');
      component.filterValue = 'oldFilter: filterValue1';
      component.toggleKeyword(keywordFilter, htmlElement);
      expect(htmlElement.focus).toHaveBeenCalled();
      expect(keywordFilter.toggleKeyword).toHaveBeenCalledWith(
        'oldFilter: filterValue1',
      );
      expect(component.filterValue).toContain('oldFilter: filterValue1');
      expect(component.filterValue).toContain('newFilter: filterValue2');
      expect(fetchDataSpy).toHaveBeenCalled();
    });
  });
});
