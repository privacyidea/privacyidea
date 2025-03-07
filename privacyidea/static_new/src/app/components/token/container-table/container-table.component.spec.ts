import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
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
      'toggleKeywordInFilter',
      'parseFilterString',
      'getFilterIconName',
      'getClassForColumnKey',
      'isFilterSelected',
      'isLink',
      'getClassForColumn',
      'getDisplayText',
      'getSpanClassForState',
      'getDisplayTextForState',
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
    tableUtilsServiceSpy.toggleKeywordInFilter.and.callFake(
      (currentFilter: string, keyword: string) => {
        return currentFilter.includes(keyword)
          ? currentFilter.replace(keyword, '')
          : currentFilter.concat(` ${keyword}`);
      },
    );

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
    it('should fetch data if authenticated', () => {
      expect(authServiceSpy.isAuthenticatedUser).toHaveBeenCalled();
      expect(containerServiceSpy.getContainerData).toHaveBeenCalled();
      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });

    it('should navigate if not authenticated', () => {
      authServiceSpy.isAuthenticatedUser.and.returnValue(false);

      fixture = TestBed.createComponent(ContainerTableComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['']);
    });
  });

  describe('fetchContainerData()', () => {
    it('should call containerService.getContainerData', () => {
      containerServiceSpy.getContainerData.calls.reset();
      component['fetchContainerData']();
      expect(containerServiceSpy.getContainerData).toHaveBeenCalledWith(
        component.pageIndex + 1,
        component.pageSize,
        component.sortby_sortdir,
        component.filterValue,
      );
    });

    it('should handle error response from getContainerData', () => {
      containerServiceSpy.getContainerData.and.returnValue(
        throwError(() => new Error('Some error')),
      );

      component['fetchContainerData']();
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to get container data. ',
      );
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

  describe('handlePageEvent()', () => {
    it('should set pageSize, pageIndex and call fetchContainerData', () => {
      spyOn<any>(component, 'fetchContainerData').and.callThrough();
      component.handlePageEvent({ pageIndex: 2, pageSize: 15 } as any);
      expect(component.pageIndex).toBe(2);
      expect(component.pageSize).toBe(15);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('handleSortEvent()', () => {
    it('should set sortby_sortdir and reset pageIndex to 0 and fetch data', () => {
      component.sort = { active: 'type', direction: 'asc' } as any;
      spyOn<any>(component, 'fetchContainerData').and.callThrough();

      component.handleSortEvent();
      expect(component.sortby_sortdir).toEqual({
        active: 'type',
        direction: 'asc',
      });
      expect(component.pageIndex).toBe(0);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('handleFilterInput()', () => {
    it('should set filterValue, reset pageIndex, and call fetchContainerData', () => {
      spyOn<any>(component, 'fetchContainerData').and.callThrough();
      const mockEvent = {
        target: { value: ' filterValue ' },
      } as unknown as Event;

      component.handleFilterInput(mockEvent);
      expect(component.filterValue).toBe('filterValue');
      expect(component.pageIndex).toBe(0);
      expect(component['fetchContainerData']).toHaveBeenCalled();
    });
  });

  describe('toggleKeywordInFilter()', () => {
    it('should use tableUtilsService to toggle keyword and re-fetch data', () => {
      spyOn<any>(component, 'fetchContainerData').and.callThrough();
      const inputEl = document.createElement('input');
      inputEl.value = 'status';

      component.toggleKeywordInFilter('type', inputEl);

      expect(inputEl.value).toContain('type');
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

    it('should call openSnackBar on error', () => {
      containerServiceSpy.toggleActive.and.returnValue(
        throwError(() => new Error('Toggle error')),
      );
      const mockElement = { serial: 'Mock serial', states: ['active'] };

      component.handleStateClick(mockElement);

      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to toggle active. ',
      );
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
