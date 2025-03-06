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
import { KeywordFilter } from '../../../services/keyword_filter';
import { FetchDataResponse } from '../../universals/filter-table/filter-table.component';
import { ContainerData } from '../../../model/container/container-data';

describe('ContainerTableComponent', () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;

  let authServiceSpy: jasmine.SpyObj<AuthService>;
  let containerServiceSpy: jasmine.SpyObj<ContainerService>;
  let notificationServiceSpy: jasmine.SpyObj<NotificationService>;
  let tableUtilsServiceSpy: jasmine.SpyObj<TableUtilsService>;
  let keywordFilterSpy: jasmine.SpyObj<KeywordFilter>;
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
    keywordFilterSpy = jasmine.createSpyObj('KeywordFilter', [
      'toggleKeyword',
      'keyword',
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
    keywordFilterSpy.toggleKeyword.and.callFake((currentFilter: string) => {
      return currentFilter.includes(keywordFilterSpy.keyword)
        ? currentFilter.replace(keywordFilterSpy.keyword, '')
        : currentFilter.concat(` ${keywordFilterSpy.keyword}`);
    });

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

  describe('fetchDataHandler()', () => {
    it('should call containerService.getContainerData', () => {
      containerServiceSpy.getContainerData.calls.reset();
      component.fetchDataHandler({
        pageIndex: 0,
        pageSize: 10,
        sortby_sortdir: { active: 'serial', direction: 'asc' },
        filterValue: '',
      });
      expect(containerServiceSpy.getContainerData).toHaveBeenCalledWith(
        0,
        10,
        { active: 'serial', direction: 'asc' },
        '',
      );
    });

    it('should handle error response from getContainerData', () => {
      containerServiceSpy.getContainerData.and.returnValue(
        throwError(() => new Error('Some error')),
      );

      component.fetchDataHandler({
        pageIndex: 0,
        pageSize: 10,
        sortby_sortdir: { active: 'serial', direction: 'asc' },
        filterValue: '',
      });
      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to get container data. ',
      );
    });
  });

  describe('processDataSource()', () => {
    it('should transform users array to "users" and "user_realm" fields', () => {
      const mockResponse: FetchDataResponse = {
        result: {
          value: {
            containers: [
              {
                serial: 'Mock serial',
                type: 'hotp',
                states: ['active'],
                description: 'test description',
                users: [
                  {
                    user_id: '1',
                    user_name: 'admin_user',
                    user_realm: 'realm1',
                    user_resolver: 'resolver1',
                  },
                ],
                user_realm: 'realm1',
                realms: 'realm1',
              },
              {
                serial: 'Mock serial 2',
                type: 'hotp',
                states: ['deactivated'],
                description: 'test description',
                users: [],
                user_realm: 'realm1',
                realms: 'realm1',
              },
            ],
          },
        },
      };
      const [count, dataSource] = component.processDataSource(mockResponse);
      expect(count).toBe(1);
      const tableData = dataSource.data;
      expect(tableData[0].serial).toBe('Mock serial');
      expect(tableData[0].type).toBe('hotp');
      expect(tableData[0].states).toEqual(['active']);
      expect(tableData[0].description).toBe('test description');
      expect(tableData[0].users![0].user_realm).toBe('realm1');
      expect(tableData[0].users![0].user_name).toBe('admin_user');
      expect(tableData[1].serial).toBe('Mock serial 2');
      expect(tableData[1].type).toBe('hotp');
      expect(tableData[1].states).toEqual(['deactivated']);
      expect(tableData[1].description).toBe('test description');
      expect(tableData[1].users).toEqual([]);
    });

    it('should call openSnackBar on error', () => {
      containerServiceSpy.toggleActive.and.returnValue(
        throwError(() => new Error('Toggle error')),
      );
      const mockElement = { serial: 'Mock serial', states: ['active'] };

      component.onClickToggleActive(mockElement);

      expect(notificationServiceSpy.openSnackBar).toHaveBeenCalledWith(
        'Failed to toggle active. ',
      );
    });
  });

  describe('containerSelected()', () => {
    it('should set containerSerial and selectedContent', () => {
      component.selectContainer('new serial');
      expect(component.containerSerial()).toBe('new serial');
      expect(component.selectedContent()).toBe('container_details');
    });
  });
});
