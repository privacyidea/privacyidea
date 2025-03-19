import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ContainerTableComponent } from './container-table.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AuthService } from '../../../services/auth/auth.service';
import { ContainerService } from '../../../services/container/container.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { Router } from '@angular/router';
import { signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { Sort } from '@angular/material/sort';
import { MatPaginator } from '@angular/material/paginator';

describe('ContainerTableComponent', () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;

  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let containerServiceSpy: jasmine.SpyObj<ContainerService>;
  let notificationServiceSpy: jasmine.SpyObj<NotificationService>;
  let tableUtilsServiceSpy: jasmine.SpyObj<TableUtilsService>;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    authServiceSpy = jasmine.createSpyObj('AuthService', [
      'isAuthenticatedUser',
    ]);
    containerServiceSpy = jasmine.createSpyObj('ContainerService', [
      'apiFilter',
      'advancedApiFilter',
      'getContainerData',
      'toggleActive',
    ]);
    notificationServiceSpy = jasmine.createSpyObj('NotificationService', [
      'openSnackBar',
    ]);
    tableUtilsServiceSpy = jasmine.createSpyObj('TableUtilsService', [
      'parseFilterString',
      'getFilterIconName',
      'getClassForColumnKey',
      'isFilterSelected',
      'isLink',
      'getClassForColumn',
      'getDisplayText',
      'getSpanClassForState',
      'getDisplayTextForState',
      'handleFilterInput',
      'handlePageEvent',
      'handleSortEvent',
    ]);

    routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    containerServiceSpy.apiFilter = ['serial', 'type', 'states', 'description'];
    containerServiceSpy.advancedApiFilter = ['realm', 'users'];

    authServiceSpy.isAuthenticatedUser.and.returnValue(true);
    containerServiceSpy.getContainerData.and.returnValue(
      of({
        result: {
          value: {
            count: 1,
            containers: [
              {
                serial: 'Mock serail',
                type: 'hopt',
                states: ['active'],
                description: 'desc',
                users: [
                  {
                    user_name: 'test_user',
                    user_realm: 'realm1',
                  },
                ],
                realms: 'containerRealm',
              },
            ],
          },
        },
      }),
    );

    containerServiceSpy.toggleActive.and.returnValue(of({}));

    routerSpy.navigate.and.returnValue(Promise.resolve(true));

    await TestBed.configureTestingModule({
      imports: [ContainerTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceSpy },
        { provide: ContainerService, useValue: containerServiceSpy },
        { provide: NotificationService, useValue: notificationServiceSpy },
        { provide: TableUtilsService, useValue: tableUtilsServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTableComponent);
    component = fixture.componentInstance;

    component.containerSerial = signal('Mock container');
    component.selectedContent = signal('container_overview');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('constructor', () => {
    it('should fetch data', () => {
      expect(containerServiceSpy.getContainerData).toHaveBeenCalled();
      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });
  });

  describe('fetchContainerData()', () => {
    it('should call containerService.getContainerData', () => {
      containerServiceSpy.getContainerData.calls.reset();
      component['fetchContainerData']();
      expect(containerServiceSpy.getContainerData).toHaveBeenCalledWith({
        page: component.pageIndex() + 1,
        pageSize: component.pageSize(),
        sort: component.sortby_sortdir(),
        filterValue: component.filterValue(),
      });
    });
  });

  describe('processDataSource()', () => {
    it('should transform users array to "users" and "user_realm" fields', () => {
      const mockData = [
        {
          serial: 'Mock serial',
          type: 'hotp',
          states: 'active',
          description: 'test description',
          users: [{ user_name: 'admin_user', user_realm: 'realm1' }],
        },
        {
          serial: 'Mock serial',
          type: 'hotp',
          states: ['deactivated'],
          description: 'test description',
          users: [],
        },
      ];
      component['processDataSource'](mockData);

      const tableData = component.dataSource().data;
      expect(tableData[0].users).toBe('admin_user');
      expect(tableData[0].user_realm).toBe('realm1');
      expect(tableData[1].users).toBe('');
      expect(tableData[1].user_realm).toBe('');
    });
  });

  describe('Paginator (handlePageEvent)', () => {
    it('should delegate page changes to tableUtilsService.handlePageEvent', () => {
      const paginator = fixture.debugElement.query(
        By.directive(MatPaginator),
      ).componentInstance;
      const testPageEvent = { pageIndex: 2, pageSize: 15 };

      spyOn<any>(component, 'fetchContainerData').and.callThrough();

      tableUtilsServiceSpy.handlePageEvent.and.callFake(
        (event, pageIndexSignal, pageSizeSignal) => {
          pageIndexSignal.set(event.pageIndex);
          pageSizeSignal.set(event.pageSize);
        },
      );

      paginator.page.emit(testPageEvent);
      fixture.detectChanges();

      expect(tableUtilsServiceSpy.handlePageEvent).toHaveBeenCalledWith(
        jasmine.objectContaining(testPageEvent),
        component.pageIndex,
        component.pageSize,
      );
      expect(component.pageIndex()).toBe(2);
      expect(component.pageSize()).toBe(15);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('Sort (handleSortEvent)', () => {
    it('should delegate sort changes to tableUtilsService.handleSortEvent', () => {
      const testSort: Sort = { active: 'type', direction: 'asc' };
      spyOn<any>(component, 'fetchContainerData').and.callThrough();

      tableUtilsServiceSpy.handleSortEvent.and.callFake(
        (sort, pageIndexSignal, sortbySortDirSignal, fetchDataCb) => {
          sortbySortDirSignal.set(sort);
          pageIndexSignal.set(0);
          fetchDataCb();
        },
      );

      tableUtilsServiceSpy.handleSortEvent(
        testSort,
        component.pageIndex,
        component.sortby_sortdir,
        component['fetchContainerData'],
      );
      fixture.detectChanges();

      expect(tableUtilsServiceSpy.handleSortEvent).toHaveBeenCalledWith(
        testSort,
        component.pageIndex,
        component.sortby_sortdir,
        jasmine.any(Function),
      );
      expect(component.sortby_sortdir().active).toBe('type');
      expect(component.sortby_sortdir().direction).toBe('asc');
      expect(component.pageIndex()).toBe(0);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('Filter (handleFilterInput)', () => {
    it('should delegate filter changes to tableUtilsService.handleFilterInput', () => {
      const mockEvent = {
        target: { value: '  filterValue  ' },
      } as unknown as Event;

      spyOn<any>(component, 'fetchContainerData').and.callThrough();

      tableUtilsServiceSpy.handleFilterInput.and.callFake(
        (eventArg, pageIndexSignal, filterValueSignal, fetchDataCb) => {
          const trimmed = (eventArg.target as HTMLInputElement).value.trim();
          filterValueSignal.set(trimmed);
          pageIndexSignal.set(0);
          fetchDataCb();
        },
      );

      tableUtilsServiceSpy.handleFilterInput(
        mockEvent,
        component.pageIndex,
        component.filterValue,
        component['fetchContainerData'],
      );
      fixture.detectChanges();

      expect(tableUtilsServiceSpy.handleFilterInput).toHaveBeenCalledWith(
        mockEvent,
        component.pageIndex,
        component.filterValue,
        jasmine.any(Function),
      );
      expect(component.filterValue()).toBe('filterValue');
      expect(component.pageIndex()).toBe(0);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('handleStateClick()', () => {
    it('should call toggleActive() and refetch data on success', () => {
      spyOn<any>(component, 'fetchContainerData').and.callThrough();
      const mockElement = { serial: 'Mock serial', states: ['active'] };

      component.handleStateClick(mockElement);

      expect(containerServiceSpy.toggleActive).toHaveBeenCalledWith(
        'Mock serial',
        ['active'],
      );
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('containerSelected()', () => {
    it('should set containerSerial and selectedContent', () => {
      component.containerSelected('new serial');
      expect(component.containerSerial()).toBe('new serial');
      expect(component.selectedContent()).toBe('container_details');
    });
  });
});
