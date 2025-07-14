import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ContainerTableComponent } from './container-table.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from '../../../services/auth/auth.service';
import { ContainerService } from '../../../services/container/container.service';
import { NotificationService } from '../../../services/notification/notification.service';
import { TableUtilsService } from '../../../services/table-utils/table-utils.service';
import { NavigationEnd, Router } from '@angular/router';
import { signal, WritableSignal } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Sort } from '@angular/material/sort';
import { of } from 'rxjs';
import { TokenService } from '../../../services/token/token.service';
import { ContentService } from '../../../services/content/content.service';

function makeResource<T>(initial: T) {
  return {
    value: signal(initial) as WritableSignal<T>,
    reload: jest.fn(),
    error: jest.fn().mockReturnValue(null),
  };
}

const authServiceMock = {
  isAuthenticatedUser: jest.fn().mockReturnValue(true),
};

const tableUtilsMock = {
  // Only the bits used by this component/tests.
  recordsFromText: jest.fn().mockReturnValue({}),
  getClassForColumnKey: jest.fn().mockReturnValue(''),
  isLink: jest.fn().mockReturnValue(false),
  getSpanClassForState: jest.fn().mockReturnValue(''),
  getDisplayTextForState: jest.fn().mockReturnValue(''),
};

const notificationServiceMock = {
  openSnackBar: jest.fn(),
};

const tokenServiceMock = {
  selectedContent: signal('container_overview'),
};

const contentServiceMock = {};

const mockContainerResource = {
  result: {
    value: {
      count: 2,
      containers: [
        {
          serial: 'CONT-1',
          type: 'hotp',
          states: ['active'],
          description: 'Container 1',
          users: [{ user_name: 'user1', user_realm: 'realm1' }],
          realms: [],
        },
        {
          serial: 'CONT-2',
          type: 'totp',
          states: ['deactivated'],
          description: 'Container 2',
          users: [],
          realms: [],
        },
      ],
    },
  },
};

const containerServiceMock = {
  containerSelection: signal<any[]>([]),
  filterValue: signal<Record<string, string>>({}),
  pageSize: signal(10),
  pageIndex: signal(0),
  sort: signal<Sort>({ active: 'serial', direction: '' }),
  containerResource: makeResource(mockContainerResource),

  apiFilter: ['serial', 'type', 'states', 'description'],
  advancedApiFilter: ['realm', 'users'],

  getContainerData: jest.fn().mockReturnValue(of(mockContainerResource)),
  toggleActive: jest.fn().mockReturnValue(of({})),
  eventPageSize: 10,
};

describe('ContainerTableComponent (Jest)', () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;

  beforeEach(async () => {
    TestBed.resetTestingModule();
    await TestBed.configureTestingModule({
      imports: [ContainerTableComponent, BrowserAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authServiceMock },
        { provide: ContainerService, useValue: containerServiceMock },
        { provide: TableUtilsService, useValue: tableUtilsMock },
        { provide: NotificationService, useValue: notificationServiceMock },
        { provide: TokenService, useValue: tokenServiceMock },
        { provide: ContentService, useValue: contentServiceMock },
        {
          provide: Router,
          useValue: {
            navigate: jest.fn(),
            events: of(new NavigationEnd(0, '/', '/')),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTableComponent);
    component = fixture.componentInstance;

    component.selectedContent = signal('container_overview');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('#handleStateClick', () => {
    it('calls toggleActive and reloads data', () => {
      const element = { serial: 'CONT-1', states: ['active'] } as any;
      component.handleStateClick(element);

      expect(containerServiceMock.toggleActive).toHaveBeenCalledWith('CONT-1', [
        'active',
      ]);
      expect(containerServiceMock.containerResource.reload).toHaveBeenCalled();
    });
  });

  describe('#onPageEvent', () => {
    it('updates page index, size and eventPageSize', () => {
      const event: PageEvent = {
        pageIndex: 2,
        pageSize: 15,
        length: 100,
        previousPageIndex: 1,
      };

      component.onPageEvent(event);

      expect(component.pageIndex()).toBe(2);
      expect(component.pageSize()).toBe(15);
      expect(containerServiceMock.eventPageSize).toBe(15);
    });
  });

  describe('#onSortEvent', () => {
    it('updates the sort signal', () => {
      const sort: Sort = { active: 'type', direction: 'asc' };

      component.onSortEvent(sort);

      const result = component.sort();
      expect(result.active).toBe('type');
      expect(result.direction).toBe('asc');
    });
  });

  describe('Selection helpers', () => {
    it('toggleAllRows selects *then* clears every row', () => {
      expect(component.isAllSelected()).toBe(false);

      component.toggleAllRows();
      expect(component.isAllSelected()).toBe(true);
      expect(component.containerSelection().length).toBe(2);

      component.toggleAllRows();
      expect(component.isAllSelected()).toBe(false);
      expect(component.containerSelection().length).toBe(0);
    });

    it('toggleRow adds and removes a single row', () => {
      const row = component.containerDataSource().data[0];

      component.toggleRow(row);
      expect(component.containerSelection()).toContain(row);

      component.toggleRow(row);
      expect(component.containerSelection()).not.toContain(row);
    });
  });
});
