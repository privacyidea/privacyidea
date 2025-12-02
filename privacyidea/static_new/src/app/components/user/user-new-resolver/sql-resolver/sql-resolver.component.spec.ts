import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SqlResolverComponent } from './sql-resolver.component';

describe('SqlResolverComponent', () => {
  let component: SqlResolverComponent;
  let fixture: ComponentFixture<SqlResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SqlResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SqlResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
